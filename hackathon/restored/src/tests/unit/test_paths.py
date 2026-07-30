"""Tests for utils/paths.py — project root resolution and data paths."""

from __future__ import annotations

from pathlib import Path

from volforecast.utils.paths import (
    configs_dir,
    correlation_cache_dir,
    cross_asset_cache_dir,
    data_path,
    iv_cache_dir,
    micro_sequences_dir,
    models_dir,
    raw_dir,
    resolve_project_root,
    rv_cache_path,
    ticks_cache_dir,
    ticks_cache_path,
    tmp_dir,
)


class TestResolveProjectRoot:
    def test_finds_repo_root(self):
        root = resolve_project_root()
        assert root.is_absolute()
        # Marker files should exist at root
        assert (root / "AGENTS.md").exists() or (root / "vol.cmd").exists()

    def test_returns_path_object(self):
        root = resolve_project_root()
        assert isinstance(root, Path)

    def test_consistent_across_calls(self):
        assert resolve_project_root() == resolve_project_root()


class TestDataPath:
    def test_category_only(self):
        p = data_path("raw")
        assert p.is_absolute()
        assert p.name == "raw"
        assert p.parent.name == "data"

    def test_category_with_filename(self):
        p = data_path("raw/ticks", "SPY.parquet")
        assert p.name == "SPY.parquet"
        assert p.parent.name == "ticks"

    def test_matches_legacy_models_dir(self):
        assert models_dir() == data_path("models")


class TestNewPathHelpers:
    """Tests for the new canonical path helpers (post-rename)."""

    def test_ticks_cache_dir(self):
        d = ticks_cache_dir()
        assert d.is_absolute()
        assert d.name == "ticks"
        assert d.parent.name == "raw"

    def test_ticks_cache_path(self):
        p = ticks_cache_path("SPY")
        assert p.name == "SPY.parquet"
        assert p.parent.name == "ticks"

    def test_ticks_matches_data_path(self):
        assert ticks_cache_path("SPY") == data_path("raw/ticks", "SPY.parquet")

    def test_iv_cache_dir_points_to_iv(self):
        d = iv_cache_dir()
        assert d.is_absolute()
        assert d.name == "iv"
        assert d.parent.name == "raw"

    def test_cross_asset_cache_dir(self):
        d = cross_asset_cache_dir()
        assert d.is_absolute()
        assert d.name == "cross_asset"
        assert d.parent.name == "raw"

    def test_correlation_cache_dir(self):
        d = correlation_cache_dir()
        assert d.is_absolute()
        assert d.name == "correlation"
        assert d.parent.name == "raw"

    def test_micro_sequences_dir(self):
        d = micro_sequences_dir()
        assert d.is_absolute()
        assert d.name == "sequences"
        assert d.parent.name == "micro"


class TestDeprecatedAliases:
    """Old function names still work and point to the new locations."""

    def test_rv_cache_path_aliases_ticks(self):
        assert rv_cache_path("SPY") == ticks_cache_path("SPY")


class TestDirHelpers:
    def test_raw_dir_absolute(self):
        d = raw_dir()
        assert d.is_absolute()
        assert d.name == "raw"
        assert d.parent.name == "data"

    def test_models_dir_absolute(self):
        d = models_dir()
        assert d.is_absolute()
        assert d.name == "models"
        assert d.parent.name == "data"

    def test_configs_dir_absolute(self):
        d = configs_dir()
        assert d.is_absolute()
        assert d.name == "configs"
        assert d.parent.name == "workspace"

    def test_tmp_dir_absolute(self):
        d = tmp_dir()
        assert d.is_absolute()
        assert d.name == "tmp"
        assert d.parent.name == "workspace"
