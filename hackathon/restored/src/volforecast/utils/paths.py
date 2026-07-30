"""Project path resolution utilities.

Provides absolute paths anchored to the repo root regardless of CWD.
This is critical because vol.cmd changes to src/ before invoking Python,
so relative paths in constants.py resolve incorrectly without this.

Directory layout (post-migration)::

    data/raw/
    ├── ticks/          # L0 + L1 + noise_robust (was rv/)
    ├── iv/             # L2 options-implied (was iv_surface/)
    ├── ohlcv/          # L6 daily OHLCV
    ├── micro/          # L3 microstructure aggregates
    │   └── sequences/  # 10s bar sequences for LSTM
    ├── cross_asset/    # L4 yields, FX vol, credit vol (was macro/)
    └── correlation/    # L7 SPX implied/realized correlation
"""

from __future__ import annotations

from pathlib import Path

_MARKER_FILES = ("AGENTS.md", "vol.cmd", "vol")


def resolve_project_root() -> Path:
    """Find the repo root by walking up from this file looking for marker files.

    Returns the first ancestor directory containing AGENTS.md or vol.cmd.
    Raises RuntimeError if no marker is found (should never happen in normal use).
    """
    current = Path(__file__).resolve().parent
    # Walk up to max 10 levels (src/volforecast/utils/ -> repo root is 3 up)
    for _ in range(10):
        if any((current / marker).exists() for marker in _MARKER_FILES):
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    raise RuntimeError(
        "Could not find project root (looked for AGENTS.md or vol.cmd). "
        "Is the package installed outside the ml-vol-estimator repo?"
    )


def data_path(category: str, filename: str | None = None) -> Path:
    """Resolve a data path: {project_root}/data/{category}[/{filename}]."""
    base = resolve_project_root() / "data" / category
    if filename:
        return base / filename
    return base


# ── Canonical path helpers (new names, post-migration) ────────────────────


def raw_dir() -> Path:
    """Absolute path to data/raw/."""
    return data_path("raw")


def ticks_cache_dir() -> Path:
    """Absolute path to data/raw/ticks/ (daily RV panel parquets)."""
    return data_path("raw/ticks")


def ticks_cache_path(symbol: str) -> Path:
    """Parquet path for a symbol's daily RV panel: data/raw/ticks/{SYMBOL}.parquet."""
    return data_path("raw/ticks", f"{symbol}.parquet")


def iv_cache_dir() -> Path:
    """Absolute path to data/raw/iv/ (per-symbol IV from TSDB edrvol_)."""
    return data_path("raw/iv")


def iv_cache_path(symbol: str) -> Path:
    """Parquet path for a symbol's IV surface: data/raw/iv/{SYMBOL}.parquet."""
    return data_path("raw/iv", f"{symbol}.parquet")


def ohlcv_cache_dir() -> Path:
    """Absolute path to data/raw/ohlcv/ (daily OHLCV from TSDB)."""
    return data_path("raw/ohlcv")


def ohlcv_cache_path(symbol: str) -> Path:
    """Parquet path for a symbol's daily OHLCV: data/raw/ohlcv/{SYMBOL}.parquet."""
    return data_path("raw/ohlcv", f"{symbol}.parquet")


def micro_cache_dir() -> Path:
    """Absolute path to data/raw/micro/ (microstructure daily aggregates)."""
    return data_path("raw/micro")


def micro_cache_path(symbol: str) -> Path:
    """Parquet path for microstructure features: data/raw/micro/{SYMBOL}.parquet."""
    return data_path("raw/micro", f"{symbol}.parquet")


def micro_sequences_dir() -> Path:
    """Absolute path to data/raw/micro/sequences/ (10s bar sequences for LSTM)."""
    return data_path("raw/micro/sequences")


def micro_staging_dir(symbol: str) -> Path:
    """Staging directory for incremental batch writes: .staging/{SYMBOL}/."""
    return data_path("raw/micro/sequences/.staging") / symbol


def cross_asset_cache_dir() -> Path:
    """Absolute path to data/raw/cross_asset/ (yields, FX vol, credit vol)."""
    return data_path("raw/cross_asset")


def correlation_cache_dir() -> Path:
    """Absolute path to data/raw/correlation/ (SPX implied/realized corr)."""
    return data_path("raw/correlation")


# ── Deprecated aliases (old names → new locations) ────────────────────────


def rv_cache_dir() -> Path:
    """Deprecated: use ticks_cache_dir(). Points to data/raw/ticks/."""
    return ticks_cache_dir()


def rv_cache_path(symbol: str) -> Path:
    """Deprecated: use ticks_cache_path(). Points to data/raw/ticks/{SYMBOL}.parquet."""
    return ticks_cache_path(symbol)


def macro_cache_dir() -> Path:
    """Deprecated: use cross_asset_cache_dir(). Points to data/raw/cross_asset/."""
    return cross_asset_cache_dir()


def macro_cache_path() -> Path:
    """Deprecated: use cross_asset_cache_dir() with specific file."""
    return data_path("raw/cross_asset", "us_macro.parquet")


# ── Non-raw path helpers ──────────────────────────────────────────────────


def processed_dir() -> Path:
    """Absolute path to data/processed/ (feature panels, merged datasets)."""
    return data_path("processed")


def models_dir() -> Path:
    """Absolute path to data/models/ (experiment artifacts)."""
    return data_path("models")


def external_dir() -> Path:
    """Absolute path to data/external/ (external downloads, calendars)."""
    return data_path("external")


def configs_dir() -> Path:
    """Absolute path to workspace/configs/ (experiment YAML configs)."""
    return resolve_project_root() / "workspace" / "configs"


def tmp_dir() -> Path:
    """Absolute path to workspace/tmp/ (ephemeral output)."""
    return resolve_project_root() / "workspace" / "tmp"


def allday_vols_cache_path() -> Path:
    """Parquet path for SPX AllDay Vols mark Kvar: data/raw/iv/SPX_allday_vols.parquet."""
    return data_path("raw/iv", "SPX_allday_vols.parquet")
