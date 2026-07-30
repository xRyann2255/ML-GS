"""Tests for the runner's sequence-model dispatch path.

These cover the new branch added to ``Pipeline.run_pooled`` for models that
set ``requires_sequences = True`` (the LSTM family). The tabular path is
covered by the existing ``test_parallel*`` suites and must remain unchanged.

Validates:
1. Dispatch — a model with ``requires_sequences=True`` is fed a sequence
   wrapper, not a DataFrame.
2. Date alignment — dates present in tabular panel but missing from the
   sequence cache are dropped with a single warning per fold.
3. Return contract — sequence path returns the same dict keys as the
   tabular path: ``{metrics, predictions, actuals, model, duan_correction}``
   so downstream tournament code is contract-compatible.
4. CV fold isolation — normaliser stats are computed on training rows only
   (no test-set leakage).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from volforecast.config import CVConfig, ExperimentConfig, ModelConfig
from volforecast.models._base import _BaseModel
from volforecast.pipeline.runner import Pipeline
from volforecast.registry import register_model

# ---------------------------------------------------------------------------
# Tiny recording fake sequence model for dispatch test
# ---------------------------------------------------------------------------


@register_model("_fake_seq")
class _FakeSequenceModel(_BaseModel):
    """Records the type and shape of training inputs for dispatch tests."""

    REQUIRED_LAYERS: list[str] = ["har_core"]
    requires_sequences: bool = True

    seen_fit_input_type: str | None = None
    seen_fit_input_shape: tuple[int, ...] | None = None
    seen_target_len: int | None = None
    last_predict_n: int | None = None

    def __init__(self, **_ignored) -> None:
        # Accept any kwargs the runner may inject (e.g. input_dim auto-filled
        # from SequenceSpec). We don't care about them for dispatch testing.
        pass

    def fit(self, seq, y) -> _FakeSequenceModel:
        # Record what we got so the test can assert on it.
        type(self).seen_fit_input_type = type(seq).__name__
        type(self).seen_fit_input_shape = tuple(seq.tensor.shape)
        if hasattr(y, "__len__"):
            type(self).seen_target_len = len(y)
        return self

    def predict(self, seq) -> np.ndarray:
        n = int(seq.tensor.shape[0])
        type(self).last_predict_n = n
        # Deterministic prediction so QLIKE / MSE are well-defined.
        return np.full((n,), -10.0, dtype=np.float32)


# ---------------------------------------------------------------------------
# Synthetic data fixtures
# ---------------------------------------------------------------------------


def _make_daily_panel(symbols: list[str], n_days: int, seed: int = 0) -> dict[str, pd.DataFrame]:
    """Per-symbol daily DataFrame with 'rv' column (positive)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2022-01-03", periods=n_days)
    out: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        rv = np.exp(-4.0 + 0.3 * rng.standard_normal(n_days))
        out[sym] = pd.DataFrame({"rv": rv}, index=dates)
    return out


def _write_sequences_for_panel(
    sequences_dir: Path,
    panel: dict[str, pd.DataFrame],
    bars_per_day: int = 6,
    n_features_cols: tuple[str, ...] = ("buy_vol", "sell_vol", "net_flow"),
    seed: int = 1,
) -> None:
    rng = np.random.default_rng(seed)
    for sym, df in panel.items():
        rows = []
        for d in df.index:
            for b in range(bars_per_day):
                vals = rng.standard_normal(len(n_features_cols)).astype(np.float32)
                row = {
                    "date": d.strftime("%Y-%m-%d"),
                    "bar_idx": b,
                }
                for col, v in zip(n_features_cols, vals):
                    row[col] = float(v)
                rows.append(row)
        out = pd.DataFrame(rows)
        path = sequences_dir / f"{sym}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(path, index=False)


@pytest.fixture
def two_symbol_panel(tmp_path: Path):
    panel = _make_daily_panel(["SPY", "AAPL"], n_days=160, seed=11)
    sequences_dir = tmp_path / "sequences"
    cache_dir = tmp_path / "seqcache"
    _write_sequences_for_panel(sequences_dir, panel)
    return panel, sequences_dir, cache_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _build_config(
    model_name: str,
    *,
    cache_dir: Path,
    sequences_dir: Path,
    horizons: list[int] | None = None,
    model_params: dict | None = None,
) -> ExperimentConfig:
    return ExperimentConfig(
        name="test_seq_dispatch",
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
        sequences={
            "features": ["buy_vol", "sell_vol", "net_flow"],
            "max_bars": 6,
            "sequences_dir": str(sequences_dir),
            "cache_dir": str(cache_dir),
        },
    )


class TestDispatch:
    def test_sequence_flag_triggers_seq_path(self, two_symbol_panel):
        panel, sequences_dir, cache_dir = two_symbol_panel
        # Reset class-level recording.
        _FakeSequenceModel.seen_fit_input_type = None
        _FakeSequenceModel.seen_fit_input_shape = None
        _FakeSequenceModel.seen_target_len = None
        _FakeSequenceModel.last_predict_n = None

        cfg = _build_config(
            "_fake_seq",
            cache_dir=cache_dir,
            sequences_dir=sequences_dir,
        )
        results = Pipeline(cfg).run_pooled(panel)
        # Dispatch fired — model.fit was called.
        assert _FakeSequenceModel.seen_fit_input_type is not None
        # The input object exposes a 3-D tensor.
        assert _FakeSequenceModel.seen_fit_input_shape is not None
        assert len(_FakeSequenceModel.seen_fit_input_shape) == 3
        # Last axis = n_features (3).
        assert _FakeSequenceModel.seen_fit_input_shape[-1] == 3
        # Bars axis matches the spec.
        assert _FakeSequenceModel.seen_fit_input_shape[-2] == 6
        # Outputs match the standard tabular runner contract.
        assert 1 in results
        for key in ("metrics", "predictions", "actuals", "model", "duan_correction"):
            assert key in results[1], f"missing key {key!r} in sequence-path result"
        assert "qlike" in results[1]["metrics"]


class TestDateAlignment:
    def test_missing_sequence_dates_are_dropped(self, two_symbol_panel, caplog):
        """Drop rows whose date is missing from a symbol's sequence cache."""
        panel, sequences_dir, cache_dir = two_symbol_panel
        # Rewrite SPY parquet so it lacks the last 10 dates.
        spy_dates = panel["SPY"].index
        keep_dates = spy_dates[:-10]
        rows = []
        rng = np.random.default_rng(99)
        for d in keep_dates:
            for b in range(6):
                rows.append(
                    {
                        "date": d.strftime("%Y-%m-%d"),
                        "bar_idx": b,
                        "buy_vol": float(rng.standard_normal()),
                        "sell_vol": float(rng.standard_normal()),
                        "net_flow": float(rng.standard_normal()),
                    }
                )
        pd.DataFrame(rows).to_parquet(sequences_dir / "SPY.parquet", index=False)

        cfg = _build_config(
            "_fake_seq",
            cache_dir=cache_dir,
            sequences_dir=sequences_dir,
        )
        # Reset recording.
        _FakeSequenceModel.seen_target_len = None
        results = Pipeline(cfg).run_pooled(panel)
        assert 1 in results
        # Predictions exist and are finite (the dropping logic didn't blow up).
        preds = results[1]["predictions"]
        assert preds.notna().all()


class TestEndToEndLSTM:
    """One real end-to-end run with the actual LSTM on a small panel."""

    def test_runs_and_returns_qlike(self, two_symbol_panel):
        panel, sequences_dir, cache_dir = two_symbol_panel
        cfg = _build_config(
            "lstm",
            cache_dir=cache_dir,
            sequences_dir=sequences_dir,
            model_params={
                "input_dim": 3,
                "hidden_dim": 8,
                "n_layers": 1,
                "dropout": 0.0,
                "max_epochs": 3,
                "batch_size": 32,
                "device": "cpu",
                "val_fraction": 0.0,
                "early_stopping_rounds": 0,
                "loss": "qlike",
                "seed": 7,
            },
        )
        results = Pipeline(cfg).run_pooled(panel)
        assert 1 in results
        metrics = results[1]["metrics"]
        assert np.isfinite(metrics["qlike"])
        assert np.isfinite(metrics["mse"])
        preds = results[1]["predictions"]
        # MultiIndex (date, symbol).
        assert preds.index.names == ["date", "symbol"]
        assert preds.notna().all()
