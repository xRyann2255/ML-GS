"""Tests for _estimate_total_folds progress bar computation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd

from volforecast.__main__ import _estimate_total_folds
from volforecast.config import CVConfig


def _mock_parquet(rows: dict[str, int]):
    """Return a side_effect for pd.read_parquet that returns DFs of given lengths."""

    def _read(path):
        symbol = Path(path).stem
        n = rows.get(symbol, 0)
        return pd.DataFrame({"rv": range(n)})

    return _read


def _mock_path_exists(rows: dict[str, int]):
    """Return a side_effect for rv_cache_path that returns Paths with .exists()."""

    class FakePath:
        def __init__(self, symbol):
            self.symbol = symbol
            self.stem = symbol

        def exists(self):
            return self.symbol in rows

        def __fspath__(self):
            return f"/fake/{self.symbol}.parquet"

        def __str__(self):
            return f"/fake/{self.symbol}.parquet"

    def _rv_cache_path(s):
        return FakePath(s)

    return _rv_cache_path


class TestEstimateTotalFolds:
    """Tests for the progress bar fold estimation."""

    def test_stub_files_excluded(self):
        """Symbols with fewer rows than train+test are ignored (the original bug)."""
        rows = {"AAPL": 2515, "SPY": 2516, "ACN": 2, "BRK.B": 4}
        cv = CVConfig(method="expanding_window", purge_gap=10, train_size=504, test_size=126)

        with (
            patch("volforecast.utils.paths.rv_cache_path", side_effect=_mock_path_exists(rows)),
            patch("pandas.read_parquet", side_effect=_mock_parquet(rows)),
        ):
            result = _estimate_total_folds(list(rows.keys()), [1, 5, 22], cv)

        assert result > 0, "Stub files should not make total folds zero"

    def test_all_stubs_falls_back_to_default(self):
        """When no symbol meets the minimum, falls back to 2500-based estimate."""
        rows = {"ACN": 2, "BRK.B": 4}
        cv = CVConfig(method="expanding_window", purge_gap=10, train_size=504, test_size=126)

        with (
            patch("volforecast.utils.paths.rv_cache_path", side_effect=_mock_path_exists(rows)),
            patch("pandas.read_parquet", side_effect=_mock_parquet(rows)),
        ):
            result = _estimate_total_folds(list(rows.keys()), [1, 5, 22], cv)

        # With n_dates_raw=2500, should get positive folds
        assert result > 0

    def test_empty_symbols_falls_back(self):
        """Empty symbol list uses default 2500."""
        cv = CVConfig(method="expanding_window", purge_gap=10, train_size=504, test_size=126)
        result = _estimate_total_folds([], [1, 5, 22], cv)
        assert result > 0

    def test_typical_config_gives_45(self):
        """With ~2515 rows and train=504/test=126/purge=10, expect 45 folds for h=1,5,22."""
        rows = {"AAPL": 2515, "SPY": 2516, "MSFT": 2515}
        cv = CVConfig(method="expanding_window", purge_gap=10, train_size=504, test_size=126)

        with (
            patch("volforecast.utils.paths.rv_cache_path", side_effect=_mock_path_exists(rows)),
            patch("pandas.read_parquet", side_effect=_mock_parquet(rows)),
        ):
            result = _estimate_total_folds(list(rows.keys()), [1, 5, 22], cv)

        assert result == 45

    def test_uses_max_not_min(self):
        """Should use the longest qualifying symbol, not the shortest."""
        rows = {"SHORT": 700, "LONG": 2515}
        cv = CVConfig(method="expanding_window", purge_gap=10, train_size=504, test_size=126)

        with (
            patch("volforecast.utils.paths.rv_cache_path", side_effect=_mock_path_exists(rows)),
            patch("pandas.read_parquet", side_effect=_mock_parquet(rows)),
        ):
            result = _estimate_total_folds(list(rows.keys()), [1, 5, 22], cv)

        # With max=2515, expect 45. With min=700 would get ~3.
        assert result == 45

    def test_single_horizon(self):
        """Single horizon should give 15 folds with standard config."""
        rows = {"SPY": 2516}
        cv = CVConfig(method="expanding_window", purge_gap=10, train_size=504, test_size=126)

        with (
            patch("volforecast.utils.paths.rv_cache_path", side_effect=_mock_path_exists(rows)),
            patch("pandas.read_parquet", side_effect=_mock_parquet(rows)),
        ):
            result = _estimate_total_folds(["SPY"], [1], cv)

        assert result == 15

    def test_default_cv_values(self):
        """When train_size/test_size are None, defaults (252/63) are used."""
        rows = {"SPY": 2516}
        cv = CVConfig(method="expanding_window", purge_gap=5, train_size=None, test_size=None)

        with (
            patch("volforecast.utils.paths.rv_cache_path", side_effect=_mock_path_exists(rows)),
            patch("pandas.read_parquet", side_effect=_mock_parquet(rows)),
        ):
            result = _estimate_total_folds(["SPY"], [1], cv)

        # n_dates = 2516 - 22 - 1 = 2493, purge=5, folds = (2493-252-5-63)//63+1 = 35
        assert result == 35
