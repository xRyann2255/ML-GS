"""Unit test configuration.

Autouse isolation fixtures keep unit tests from polluting the real workspace
(e.g. the per-fold LSTM training cache under ``data/models/lstm_cache``).
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_fold_cache(tmp_path_factory, monkeypatch):
    """Redirect the fold-cache default root to a per-test tmp directory.

    Tests that don't explicitly set ``ExperimentConfig.fold_cache_dir`` would
    otherwise read/write under the real ``data/models/lstm_cache``. That
    causes flakiness: artifacts persist across runs and re-trigger cache HITs
    in tests that depend on ``model.fit`` being called.
    """
    tmp_root: Path = tmp_path_factory.mktemp("fold_cache_isolated")

    from volforecast.pipeline import fold_cache as _fc

    def _isolated_resolve(config=None, cache_root=None):
        if cache_root is not None:
            return Path(cache_root)
        if config is not None and getattr(config, "fold_cache_dir", None):
            return Path(config.fold_cache_dir)
        return tmp_root

    monkeypatch.setattr(_fc, "resolve_cache_root", _isolated_resolve)
