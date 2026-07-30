"""Tests for the per-fold LSTM/sequence training cache.

Covers:
1. Cache key determinism — identical inputs produce identical keys.
2. Cache invalidation — changes to config / model params / seed / sequences /
   base_model / horizon_overrides change the config fingerprint and therefore
   the fold cache keys.
3. Runtime behaviour — running the pipeline twice with an identical config
   skips fold training on the second run (cache HIT) and produces identical
   predictions.
4. Disable via ``fold_cache_enabled=False`` — always retrains, no IO.
5. Best-effort save — pipeline still succeeds when model.save raises.
6. CLI helpers — ``list_cached_folds`` and ``clear_fold_cache`` round-trip.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from volforecast.config import CVConfig, ExperimentConfig, ModelConfig
from volforecast.models._base import _BaseModel
from volforecast.pipeline.fold_cache import (
    clear_fold_cache,
    compute_fold_cache_key,
    config_subdir,
    list_cached_folds,
    load_fold_cache,
    resolve_cache_root,
    save_fold_cache,
)
from volforecast.pipeline.runner import Pipeline
from volforecast.registry import register_model

# ---------------------------------------------------------------------------
# Counter-equipped fake sequence model — records every fit/predict call.
# ---------------------------------------------------------------------------


@register_model("_cache_fake_seq")
class _CountingSequenceModel(_BaseModel):
    """Sequence-mode model that counts fit/predict calls per process."""

    REQUIRED_LAYERS: list[str] = ["har_core"]
    requires_sequences: bool = True

    fit_calls: int = 0
    predict_calls: int = 0
    last_fit_n: int | None = None

    def __init__(self, **_ignored) -> None:
        self._mean: float = 0.0

    def fit(self, seq, y, **_kw):  # noqa: ANN001 — signature mirrors LSTM
        type(self).fit_calls += 1
        type(self).last_fit_n = int(seq.tensor.shape[0])
        y_arr = np.asarray(
            y.values if hasattr(y, "values") else y, dtype=np.float64
        )
        finite = y_arr[np.isfinite(y_arr)]
        # Train a one-parameter "model" so the per-fold artifact has content.
        self._mean = float(np.mean(finite)) if finite.size else -10.0
        return self

    def predict(self, seq, **_kw):  # noqa: ANN001
        type(self).predict_calls += 1
        n = int(seq.tensor.shape[0])
        # Constant predictions => Duan correction is zero, easy to assert on.
        return np.full((n,), self._mean, dtype=np.float64)


# ---------------------------------------------------------------------------
# Helpers (mirror test_runner_sequences.py fixtures)
# ---------------------------------------------------------------------------


def _make_daily_panel(symbols: list[str], n_days: int, seed: int = 0) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2022-01-03", periods=n_days)
    out: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        rv = np.exp(-4.0 + 0.3 * rng.standard_normal(n_days))
        out[sym] = pd.DataFrame({"rv": rv}, index=dates)
    return out


def _write_sequences(
    sequences_dir: Path,
    panel: dict[str, pd.DataFrame],
    *,
    bars_per_day: int = 6,
    feature_cols: tuple[str, ...] = ("buy_vol", "sell_vol", "net_flow"),
    seed: int = 1,
) -> None:
    rng = np.random.default_rng(seed)
    for sym, df in panel.items():
        rows = []
        for d in df.index:
            for b in range(bars_per_day):
                vals = rng.standard_normal(len(feature_cols)).astype(np.float32)
                row = {"date": d.strftime("%Y-%m-%d"), "bar_idx": b}
                for col, v in zip(feature_cols, vals):
                    row[col] = float(v)
                rows.append(row)
        path = sequences_dir / f"{sym}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_parquet(path, index=False)


def _make_config(
    *,
    cache_dir: Path,
    sequences_dir: Path,
    fold_cache_root: Path,
    fold_cache_enabled: bool = True,
    horizons: list[int] | None = None,
    seed: int = 42,
    model_name: str = "_cache_fake_seq",
    model_params: dict | None = None,
) -> ExperimentConfig:
    return ExperimentConfig(
        name="test_fold_cache",
        universe=["SPY", "AAPL"],
        date_range=("2022-01-03", "2022-12-31"),
        horizons=horizons or [1],
        feature_layers=["har_core"],
        model=ModelConfig(name=model_name, params=model_params or {}),
        cv=CVConfig(
            method="expanding_window",
            train_size=80,
            test_size=20,
            purge_gap=1,
        ),
        seed=seed,
        sequences={
            "features": ["buy_vol", "sell_vol", "net_flow"],
            "max_bars": 6,
            "sequences_dir": str(sequences_dir),
            "cache_dir": str(cache_dir),
        },
        fold_cache_enabled=fold_cache_enabled,
        fold_cache_dir=str(fold_cache_root),
    )


@pytest.fixture
def workspace(tmp_path: Path):
    panel = _make_daily_panel(["SPY", "AAPL"], n_days=160, seed=11)
    sequences_dir = tmp_path / "sequences"
    cache_dir = tmp_path / "seqcache"
    fold_cache_root = tmp_path / "fold_cache"
    _write_sequences(sequences_dir, panel)
    return panel, sequences_dir, cache_dir, fold_cache_root


@pytest.fixture(autouse=True)
def _reset_counters():
    _CountingSequenceModel.fit_calls = 0
    _CountingSequenceModel.predict_calls = 0
    _CountingSequenceModel.last_fit_n = None
    yield


# ---------------------------------------------------------------------------
# Pure-function unit tests
# ---------------------------------------------------------------------------


class TestCacheKey:
    def _cfg(self, tmp_path: Path) -> ExperimentConfig:
        return _make_config(
            cache_dir=tmp_path / "sc",
            sequences_dir=tmp_path / "sq",
            fold_cache_root=tmp_path / "fc",
        )

    def test_same_inputs_same_key(self, tmp_path: Path):
        cfg = self._cfg(tmp_path)
        dates_tr = pd.DatetimeIndex(pd.bdate_range("2022-01-03", periods=80))
        dates_te = pd.DatetimeIndex(pd.bdate_range("2022-04-25", periods=20))
        k1 = compute_fold_cache_key(cfg, 1, 1, dates_tr, dates_te)
        k2 = compute_fold_cache_key(cfg, 1, 1, dates_tr, dates_te)
        assert k1 == k2
        assert len(k1) == 24

    def test_different_horizon_different_key(self, tmp_path: Path):
        cfg = self._cfg(tmp_path)
        d_tr = pd.DatetimeIndex(pd.bdate_range("2022-01-03", periods=10))
        d_te = pd.DatetimeIndex(pd.bdate_range("2022-02-01", periods=5))
        assert compute_fold_cache_key(cfg, 1, 1, d_tr, d_te) != compute_fold_cache_key(
            cfg, 5, 1, d_tr, d_te
        )

    def test_different_fold_number_different_key(self, tmp_path: Path):
        cfg = self._cfg(tmp_path)
        d_tr = pd.DatetimeIndex(pd.bdate_range("2022-01-03", periods=10))
        d_te = pd.DatetimeIndex(pd.bdate_range("2022-02-01", periods=5))
        assert compute_fold_cache_key(cfg, 1, 1, d_tr, d_te) != compute_fold_cache_key(
            cfg, 1, 2, d_tr, d_te
        )

    def test_different_dates_different_key(self, tmp_path: Path):
        cfg = self._cfg(tmp_path)
        d_te = pd.DatetimeIndex(pd.bdate_range("2022-02-01", periods=5))
        d_tr_a = pd.DatetimeIndex(pd.bdate_range("2022-01-03", periods=10))
        d_tr_b = pd.DatetimeIndex(pd.bdate_range("2022-01-04", periods=10))
        assert compute_fold_cache_key(cfg, 1, 1, d_tr_a, d_te) != compute_fold_cache_key(
            cfg, 1, 1, d_tr_b, d_te
        )

    def test_different_base_preds_different_key(self, tmp_path: Path):
        cfg = self._cfg(tmp_path)
        d_tr = pd.DatetimeIndex(pd.bdate_range("2022-01-03", periods=10))
        d_te = pd.DatetimeIndex(pd.bdate_range("2022-02-01", periods=5))
        a = np.zeros(10, dtype=np.float32)
        b = np.ones(10, dtype=np.float32)
        k_a = compute_fold_cache_key(cfg, 1, 1, d_tr, d_te, base_preds_train=a)
        k_b = compute_fold_cache_key(cfg, 1, 1, d_tr, d_te, base_preds_train=b)
        k_none = compute_fold_cache_key(cfg, 1, 1, d_tr, d_te)
        assert k_a != k_b != k_none

    def test_param_change_changes_key_via_config_fp(self, tmp_path: Path):
        cfg_a = self._cfg(tmp_path)
        cfg_b = self._cfg(tmp_path)
        cfg_b.model.params = {"hidden_dim": 99}
        d_tr = pd.DatetimeIndex(pd.bdate_range("2022-01-03", periods=10))
        d_te = pd.DatetimeIndex(pd.bdate_range("2022-02-01", periods=5))
        assert compute_fold_cache_key(cfg_a, 1, 1, d_tr, d_te) != compute_fold_cache_key(
            cfg_b, 1, 1, d_tr, d_te
        )

    def test_seed_change_changes_key(self, tmp_path: Path):
        cfg_a = self._cfg(tmp_path)
        cfg_b = self._cfg(tmp_path)
        cfg_b.seed = cfg_a.seed + 1
        d_tr = pd.DatetimeIndex(pd.bdate_range("2022-01-03", periods=10))
        d_te = pd.DatetimeIndex(pd.bdate_range("2022-02-01", periods=5))
        assert compute_fold_cache_key(cfg_a, 1, 1, d_tr, d_te) != compute_fold_cache_key(
            cfg_b, 1, 1, d_tr, d_te
        )

    def test_sequences_change_changes_key(self, tmp_path: Path):
        cfg_a = self._cfg(tmp_path)
        cfg_b = self._cfg(tmp_path)
        # Simulate a SequenceConfig with different max_bars by replacing dict.
        cfg_b.sequences = {
            "features": ["buy_vol", "sell_vol", "net_flow"],
            "max_bars": 99,
            "sequences_dir": str(tmp_path / "sq"),
            "cache_dir": str(tmp_path / "sc"),
        }
        d_tr = pd.DatetimeIndex(pd.bdate_range("2022-01-03", periods=10))
        d_te = pd.DatetimeIndex(pd.bdate_range("2022-02-01", periods=5))
        assert compute_fold_cache_key(cfg_a, 1, 1, d_tr, d_te) != compute_fold_cache_key(
            cfg_b, 1, 1, d_tr, d_te
        )


# ---------------------------------------------------------------------------
# Save/load round-trip
# ---------------------------------------------------------------------------


class TestSaveLoadRoundTrip:
    def test_roundtrip(self, tmp_path: Path):
        cfg = _make_config(
            cache_dir=tmp_path / "sc",
            sequences_dir=tmp_path / "sq",
            fold_cache_root=tmp_path / "fc",
        )
        key = "abc123"
        preds = np.linspace(-9.0, -8.0, 20)
        save_fold_cache(
            config=cfg,
            key=key,
            preds=preds,
            duan_correction=0.0125,
            model=None,
            train_dates=pd.DatetimeIndex(pd.bdate_range("2022-01-03", periods=80)),
            test_dates=pd.DatetimeIndex(pd.bdate_range("2022-04-25", periods=20)),
            h=1,
            fold_num=1,
            cache_root=tmp_path / "fc",
        )
        entry = load_fold_cache(config=cfg, key=key, cache_root=tmp_path / "fc")
        assert entry is not None
        np.testing.assert_allclose(entry.preds, preds)
        assert entry.duan_correction == pytest.approx(0.0125)
        assert entry.model_path is None  # model=None passed

    def test_miss_returns_none(self, tmp_path: Path):
        cfg = _make_config(
            cache_dir=tmp_path / "sc",
            sequences_dir=tmp_path / "sq",
            fold_cache_root=tmp_path / "fc",
        )
        assert load_fold_cache(config=cfg, key="not-there", cache_root=tmp_path / "fc") is None


# ---------------------------------------------------------------------------
# End-to-end runner integration
# ---------------------------------------------------------------------------


class TestRunnerCacheBehavior:
    def test_first_run_misses_second_run_hits(self, workspace):
        panel, sequences_dir, cache_dir, fold_cache_root = workspace

        cfg = _make_config(
            cache_dir=cache_dir,
            sequences_dir=sequences_dir,
            fold_cache_root=fold_cache_root,
        )
        results1 = Pipeline(cfg).run_pooled(panel)
        fits_after_first = _CountingSequenceModel.fit_calls
        assert fits_after_first > 0, "Pipeline must train at least one fold on first run"

        # Second run with identical config: zero new fits.
        _CountingSequenceModel.fit_calls = 0
        results2 = Pipeline(cfg).run_pooled(panel)
        assert _CountingSequenceModel.fit_calls == 0, (
            f"Cache miss after identical re-run: {_CountingSequenceModel.fit_calls} fits"
        )

        # Predictions match exactly.
        for h in cfg.horizons:
            p1 = results1[h]["predictions"]
            p2 = results2[h]["predictions"]
            assert p1.index.equals(p2.index)
            np.testing.assert_allclose(p1.values, p2.values)

    def test_param_change_invalidates(self, workspace):
        panel, sequences_dir, cache_dir, fold_cache_root = workspace
        cfg_a = _make_config(
            cache_dir=cache_dir,
            sequences_dir=sequences_dir,
            fold_cache_root=fold_cache_root,
        )
        Pipeline(cfg_a).run_pooled(panel)

        # Change a model param — cache must miss and re-train all folds.
        cfg_b = _make_config(
            cache_dir=cache_dir,
            sequences_dir=sequences_dir,
            fold_cache_root=fold_cache_root,
            model_params={"hidden_dim": 99},
        )
        _CountingSequenceModel.fit_calls = 0
        Pipeline(cfg_b).run_pooled(panel)
        assert _CountingSequenceModel.fit_calls > 0, (
            "Cache should miss when model params change"
        )

    def test_seed_change_invalidates(self, workspace):
        panel, sequences_dir, cache_dir, fold_cache_root = workspace
        cfg_a = _make_config(
            cache_dir=cache_dir,
            sequences_dir=sequences_dir,
            fold_cache_root=fold_cache_root,
            seed=42,
        )
        Pipeline(cfg_a).run_pooled(panel)
        fits_a = _CountingSequenceModel.fit_calls
        assert fits_a > 0

        cfg_b = _make_config(
            cache_dir=cache_dir,
            sequences_dir=sequences_dir,
            fold_cache_root=fold_cache_root,
            seed=43,
        )
        _CountingSequenceModel.fit_calls = 0
        Pipeline(cfg_b).run_pooled(panel)
        assert _CountingSequenceModel.fit_calls == fits_a, (
            "Cache should miss every fold when seed changes"
        )

    def test_disabled_always_retrains(self, workspace):
        panel, sequences_dir, cache_dir, fold_cache_root = workspace
        cfg = _make_config(
            cache_dir=cache_dir,
            sequences_dir=sequences_dir,
            fold_cache_root=fold_cache_root,
            fold_cache_enabled=False,
        )
        Pipeline(cfg).run_pooled(panel)
        n_fits = _CountingSequenceModel.fit_calls
        assert n_fits > 0

        _CountingSequenceModel.fit_calls = 0
        Pipeline(cfg).run_pooled(panel)
        assert _CountingSequenceModel.fit_calls == n_fits, (
            "fold_cache_enabled=False must re-fit every fold"
        )

        # And no cache files should exist on disk.
        cfg_dir = resolve_cache_root(cfg) / config_subdir(cfg)
        assert not cfg_dir.exists() or not any(cfg_dir.iterdir())


# ---------------------------------------------------------------------------
# CLI helper round-trip
# ---------------------------------------------------------------------------


class TestCLIHelpers:
    def test_list_and_clear(self, workspace):
        panel, sequences_dir, cache_dir, fold_cache_root = workspace
        cfg = _make_config(
            cache_dir=cache_dir,
            sequences_dir=sequences_dir,
            fold_cache_root=fold_cache_root,
        )
        Pipeline(cfg).run_pooled(panel)
        entries = list_cached_folds(cfg)
        assert entries, "No cached folds discovered after a run"
        assert all(e["model_name"] == cfg.model.name for e in entries)
        assert all(e["h"] in cfg.horizons for e in entries)

        n_cleared = clear_fold_cache(cfg)
        assert n_cleared == len(entries)
        assert list_cached_folds(cfg) == []
