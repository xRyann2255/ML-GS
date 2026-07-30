"""Runner integration tests for stacked / residual sequence models.

When ``ExperimentConfig.base_model`` is set AND the sequence model declares
``requires_sequences=True``, the runner must:

1. Build the base model's own tabular feature panel (its own
   ``feature_layers`` \u2014 NOT inherited from the top-level config).
2. For each CV fold: fit the base on the fold's training panel, predict on
   both train and test rows, and align by ``(date, symbol)`` to the
   sequence-pooled rows.
3. Pass the per-row aligned base predictions to ``model.fit(..., base_preds=...)``
   and ``model.predict(..., base_preds=...)``.
4. When ``config.base_model is None`` (default), the call must omit the
   ``base_preds`` kwarg entirely \u2014 backward-compatible with the existing
   trial-051 path.
5. Per-horizon overrides under ``horizon_overrides[h]['base_model']`` are
   honoured (different base model class, feature_layers, or params per
   horizon).

These tests use small fake models so we exercise the wiring without paying
for real LightGBM/LSTM compute. End-to-end with real models is exercised by
the trial-052 smoke config.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from volforecast.config import (
    BaseModelConfig,
    CVConfig,
    ExperimentConfig,
    ModelConfig,
)
from volforecast.models._base import _BaseModel
from volforecast.pipeline.runner import Pipeline
from volforecast.registry import register_model

# ---------------------------------------------------------------------------
# Fake base model: registers under a unique name, returns constant mean.
# ---------------------------------------------------------------------------


@register_model("_fake_const_base")
class _FakeConstantBaseModel(_BaseModel):
    """Tabular base whose prediction is the mean of training targets.

    Trivial enough to make algebraic assertions ("LSTM saw the right base
    preds") without depending on any real model implementation.
    """

    REQUIRED_LAYERS: list[str] = ["har_core"]
    supports_tuning = False

    def __init__(self, **_ignored) -> None:
        self._mean: float | None = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> _FakeConstantBaseModel:
        self._mean = float(np.nanmean(np.asarray(y, dtype=np.float64)))
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self._mean is None:
            raise RuntimeError("_FakeConstantBaseModel.predict before fit")
        return np.full(len(X), self._mean, dtype=np.float32)


@register_model("_fake_offset_base")
class _FakeOffsetBaseModel(_BaseModel):
    """Different base: mean(y) + 1.0. Lets per-horizon-override tests assert
    that swapping the base class actually changes the values the LSTM sees.
    """

    REQUIRED_LAYERS: list[str] = ["har_core"]
    supports_tuning = False

    def __init__(self, **_ignored) -> None:
        self._mean: float | None = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> _FakeOffsetBaseModel:
        self._mean = float(np.nanmean(np.asarray(y, dtype=np.float64))) + 1.0
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self._mean is None:
            raise RuntimeError("_FakeOffsetBaseModel.predict before fit")
        return np.full(len(X), self._mean, dtype=np.float32)


# ---------------------------------------------------------------------------
# Fake sequence model: records the base_preds it receives at fit & predict.
# ---------------------------------------------------------------------------


@register_model("_fake_seq_recorder")
class _FakeSequenceRecorder(_BaseModel):
    """Sequence-first fake that captures whether ``base_preds`` arrived.

    Class-level slots make assertions easy across the pipeline boundary
    (the runner instantiates the class itself, so we can't easily inject
    the instance to inspect).
    """

    REQUIRED_LAYERS: list[str] = ["har_core"]
    requires_sequences: bool = True
    supports_tuning = False

    # Class-level recording. Tests reset these before each Pipeline.run_pooled.
    fit_calls: list[dict] = []
    predict_calls: list[dict] = []

    def __init__(self, **_ignored) -> None:
        pass

    @classmethod
    def reset(cls) -> None:
        cls.fit_calls = []
        cls.predict_calls = []

    def fit(self, seq, y, *, base_preds=None, on_progress=None):
        _FakeSequenceRecorder.fit_calls.append(
            {
                "n_dates": int(seq.tensor.shape[0]),
                "base_preds_is_none": base_preds is None,
                "base_preds": (
                    np.asarray(base_preds, dtype=np.float64).copy()
                    if base_preds is not None
                    else None
                ),
                "y_mean": float(np.nanmean(np.asarray(y, dtype=np.float64))),
            }
        )
        return self

    def predict(self, seq, *, base_preds=None) -> np.ndarray:
        n = int(seq.tensor.shape[0])
        _FakeSequenceRecorder.predict_calls.append(
            {
                "n_dates": n,
                "base_preds_is_none": base_preds is None,
                "base_preds": (
                    np.asarray(base_preds, dtype=np.float64).copy()
                    if base_preds is not None
                    else None
                ),
            }
        )
        # Deterministic, well-defined log-RV so QLIKE is finite downstream.
        return np.full((n,), -10.0, dtype=np.float32)


# ---------------------------------------------------------------------------
# Reuse the panel + sequences fixture from test_runner_sequences.
# ---------------------------------------------------------------------------


def _make_daily_panel(symbols: list[str], n_days: int, seed: int = 0) -> dict[str, pd.DataFrame]:
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
                row = {"date": d.strftime("%Y-%m-%d"), "bar_idx": b}
                for col, v in zip(n_features_cols, vals):
                    row[col] = float(v)
                rows.append(row)
        out = pd.DataFrame(rows)
        path = sequences_dir / f"{sym}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(path, index=False)


@pytest.fixture
def small_seq_panel(tmp_path: Path):
    panel = _make_daily_panel(["SPY", "AAPL"], n_days=160, seed=11)
    sequences_dir = tmp_path / "sequences"
    cache_dir = tmp_path / "seqcache"
    _write_sequences_for_panel(sequences_dir, panel)
    return panel, sequences_dir, cache_dir


def _cfg(
    *,
    cache_dir: Path,
    sequences_dir: Path,
    base_model: BaseModelConfig | None = None,
    horizons: list[int] | None = None,
    horizon_overrides: dict | None = None,
) -> ExperimentConfig:
    return ExperimentConfig(
        name="test_runner_residual",
        universe=["SPY", "AAPL"],
        date_range=("2022-01-03", "2022-12-31"),
        horizons=horizons or [1],
        feature_layers=["har_core"],
        model=ModelConfig(name="_fake_seq_recorder", params={}),
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
        base_model=base_model,
        horizon_overrides=horizon_overrides or {},
    )


# ---------------------------------------------------------------------------
# 1. Backward compat: no base_model -> no kwarg
# ---------------------------------------------------------------------------


class TestNoBaseBackwardCompat:
    def test_no_base_model_calls_fit_without_base_preds(self, small_seq_panel):
        panel, sequences_dir, cache_dir = small_seq_panel
        _FakeSequenceRecorder.reset()
        cfg = _cfg(cache_dir=cache_dir, sequences_dir=sequences_dir, base_model=None)
        Pipeline(cfg).run_pooled(panel)
        assert _FakeSequenceRecorder.fit_calls, "fake recorder.fit was never called"
        for call in _FakeSequenceRecorder.fit_calls:
            assert call["base_preds_is_none"] is True
        for call in _FakeSequenceRecorder.predict_calls:
            assert call["base_preds_is_none"] is True


# ---------------------------------------------------------------------------
# 2. base_model wired -> kwarg supplied with correct values
# ---------------------------------------------------------------------------


class TestBaseModelWired:
    def test_base_preds_passed_and_equal_constant_mean(self, small_seq_panel):
        """_FakeConstantBaseModel predicts mean(y_train); base_preds passed
        to the LSTM must be a vector of that scalar (one per seq row)."""
        panel, sequences_dir, cache_dir = small_seq_panel
        _FakeSequenceRecorder.reset()
        cfg = _cfg(
            cache_dir=cache_dir,
            sequences_dir=sequences_dir,
            base_model=BaseModelConfig(
                name="_fake_const_base",
                feature_layers=["har_core"],
                params={},
            ),
        )
        Pipeline(cfg).run_pooled(panel)

        assert _FakeSequenceRecorder.fit_calls, "fit was not called"
        assert _FakeSequenceRecorder.predict_calls, "predict was not called"
        for call in _FakeSequenceRecorder.fit_calls:
            assert call["base_preds_is_none"] is False, (
                "base_preds kwarg was None on fit \u2014 wiring not connected"
            )
            arr = call["base_preds"]
            assert arr is not None and arr.shape[0] == call["n_dates"]
            # Constant predictor \u2014 every entry equals the same train-y mean.
            assert np.allclose(arr, arr[0])
            assert np.isfinite(arr).all()
        for call in _FakeSequenceRecorder.predict_calls:
            assert call["base_preds_is_none"] is False
            arr = call["base_preds"]
            assert arr.shape[0] == call["n_dates"]
            assert np.allclose(arr, arr[0])


# ---------------------------------------------------------------------------
# 3. Per-horizon override swaps base model class
# ---------------------------------------------------------------------------


class TestHorizonOverrideSwapsBase:
    def test_different_horizons_use_different_base_classes(self, small_seq_panel):
        """h=1 uses const base (mean), h=5 uses offset base (mean+1.0).
        After the per-horizon override resolution, the LSTM at h=5 must
        receive base_preds that are exactly 1.0 above h=1's base_preds.
        """
        panel, sequences_dir, cache_dir = small_seq_panel
        _FakeSequenceRecorder.reset()
        cfg = _cfg(
            cache_dir=cache_dir,
            sequences_dir=sequences_dir,
            horizons=[1, 5],
            base_model=BaseModelConfig(
                name="_fake_const_base",
                feature_layers=["har_core"],
                params={},
            ),
            horizon_overrides={
                5: {
                    "base_model": {
                        "name": "_fake_offset_base",
                        "feature_layers": ["har_core"],
                        "params": {},
                    }
                }
            },
        )
        Pipeline(cfg).run_pooled(panel)

        # 2 horizons \u00d7 N folds each \u2014 split fit calls by horizon order.
        # The runner iterates horizons in self.config.horizons order, and
        # for each horizon walks folds. Fit count per horizon is the same
        # because both horizons see the same panel/CV.
        n_per_horizon = len(_FakeSequenceRecorder.fit_calls) // 2
        assert n_per_horizon >= 1, "expected at least one fold per horizon"
        h1_calls = _FakeSequenceRecorder.fit_calls[:n_per_horizon]
        h5_calls = _FakeSequenceRecorder.fit_calls[n_per_horizon:]

        for h1, h5 in zip(h1_calls, h5_calls):
            arr1 = h1["base_preds"]
            arr5 = h5["base_preds"]
            assert arr1 is not None and arr5 is not None
            # Same shape per fold (same seq panel rows).
            assert arr1.shape == arr5.shape
            # Each horizon's base is constant per row (proves the base was
            # actually evaluated, not stale).
            assert np.allclose(arr1, arr1[0])
            assert np.allclose(arr5, arr5[0])
            # h=5's offset base adds +1.0 to its OWN train mean. The h=1 vs
            # h=5 target means differ by O(0.02) (h=5 is a 5-day forward log
            # mean vs h=1's 1-day), so the cross-horizon delta is dominated
            # by the +1.0 offset \u2014 must be much larger than the natural
            # inter-horizon target shift.
            delta = float(arr5[0] - arr1[0])
            assert delta > 0.5, (
                f"expected h=5 offset base (>+0.5) over h=1 const base, got delta={delta:.4f}"
            )
            assert delta < 1.5, f"expected delta close to +1.0, got {delta:.4f}"


# ---------------------------------------------------------------------------
# 4. Returned predictions equal LSTM-output + base (additive identity)
# ---------------------------------------------------------------------------


class TestResultsContract:
    def test_pipeline_returns_finite_qlike_with_base(self, small_seq_panel):
        """End-to-end smoke: pipeline runs without error and returns finite
        QLIKE when base_model is wired. The fake LSTM returns -10.0 plus the
        base; final preds must be finite for the metric to compute.
        """
        panel, sequences_dir, cache_dir = small_seq_panel
        _FakeSequenceRecorder.reset()
        cfg = _cfg(
            cache_dir=cache_dir,
            sequences_dir=sequences_dir,
            base_model=BaseModelConfig(
                name="_fake_const_base",
                feature_layers=["har_core"],
                params={},
            ),
        )
        results = Pipeline(cfg).run_pooled(panel)
        assert 1 in results
        assert np.isfinite(results[1]["metrics"]["qlike"])
        preds = results[1]["predictions"]
        assert preds.notna().all()
