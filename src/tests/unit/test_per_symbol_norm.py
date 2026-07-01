"""Tests for per-symbol normalisation (Phase 3: M1, N3).

Validates:
1. SequenceConfig accepts and exposes ``norm_mode`` field (default: "pooled").
2. Per-symbol normalisation produces different stats per symbol.
3. Single-symbol per_symbol mode is equivalent to pooled mode.
4. Normalised output retains correct padding (zeros beyond lengths).
5. Per-symbol norm uses ONLY its own symbol's rows for fitting.
6. norm_mode is threaded through _resolve_sequence_config.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import torch

from volforecast.config import SequenceConfig
from volforecast.data.sequence_cache import SequenceTensor, apply_normaliser, fit_seq_normaliser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pseudo_seq(
    n_rows: int, max_bars: int, n_features: int, *, lengths: torch.Tensor | None = None
) -> SequenceTensor:
    """Create a synthetic SequenceTensor for testing."""
    t = torch.randn(n_rows, max_bars, n_features)
    if lengths is None:
        lengths = torch.full((n_rows,), max_bars, dtype=torch.long)
    dates = pd.DatetimeIndex(pd.bdate_range("2020-01-01", periods=n_rows))
    feature_names = tuple(f"f{i}" for i in range(n_features))
    # Zero-out pad positions
    for i in range(n_rows):
        t[i, lengths[i] :] = 0.0
    return SequenceTensor(
        symbol="_test", tensor=t, lengths=lengths, dates=dates, feature_names=feature_names
    )


# ---------------------------------------------------------------------------
# N3: Config schema supports norm_mode
# ---------------------------------------------------------------------------


class TestSequenceConfigNormMode:
    """SequenceConfig correctly handles norm_mode field."""

    def test_default_is_pooled(self):
        cfg = SequenceConfig()
        assert cfg.norm_mode == "pooled"

    def test_accepts_per_symbol(self):
        cfg = SequenceConfig(norm_mode="per_symbol")
        assert cfg.norm_mode == "per_symbol"

    def test_accepts_pooled_explicit(self):
        cfg = SequenceConfig(norm_mode="pooled")
        assert cfg.norm_mode == "pooled"

    def test_from_yaml_dict(self):
        """SequenceConfig(**raw_dict) should accept norm_mode from YAML."""
        raw = {
            "features": ["log_ret", "vol_share"],
            "max_bars": 2340,
            "norm_mode": "per_symbol",
        }
        cfg = SequenceConfig(**raw)
        assert cfg.norm_mode == "per_symbol"

    def test_from_yaml_dict_missing_uses_default(self):
        """When norm_mode is absent from YAML dict, default pooled is used."""
        raw = {"features": ["log_ret"], "max_bars": 100}
        cfg = SequenceConfig(**raw)
        assert cfg.norm_mode == "pooled"


# ---------------------------------------------------------------------------
# Per-symbol normalisation logic
# ---------------------------------------------------------------------------


class TestPerSymbolNormalisation:
    """Test the per-symbol normalisation helper (to be implemented)."""

    def test_per_symbol_produces_different_stats(self):
        """Two symbols with different distributions get different normalisers."""
        from volforecast.pipeline.norm import fit_per_symbol_normaliser

        n_rows = 200
        max_bars = 50
        n_feat = 3
        # Symbol 0: mean ~5, std ~1
        # Symbol 1: mean ~-2, std ~3
        t = torch.zeros(n_rows, max_bars, n_feat)
        lengths = torch.full((n_rows,), max_bars, dtype=torch.long)
        sym_ids = torch.zeros(n_rows, dtype=torch.long)

        for i in range(n_rows):
            if i < 100:
                t[i] = torch.randn(max_bars, n_feat) * 1.0 + 5.0
                sym_ids[i] = 0
            else:
                t[i] = torch.randn(max_bars, n_feat) * 3.0 - 2.0
                sym_ids[i] = 1

        normalisers = fit_per_symbol_normaliser(t, lengths, sym_ids)
        assert 0 in normalisers
        assert 1 in normalisers
        mean0, std0 = normalisers[0]
        mean1, std1 = normalisers[1]
        # Means should be clearly different
        assert (mean0 - mean1).abs().mean() > 3.0
        # Stds should differ (1 vs ~3)
        assert (std1 / std0).mean() > 2.0

    def test_single_symbol_equivalent_to_pooled(self):
        """With only one symbol, per_symbol normaliser matches pooled."""
        from volforecast.pipeline.norm import fit_per_symbol_normaliser

        n_rows = 100
        max_bars = 30
        n_feat = 2
        t = torch.randn(n_rows, max_bars, n_feat)
        lengths = torch.full((n_rows,), max_bars, dtype=torch.long)
        sym_ids = torch.zeros(n_rows, dtype=torch.long)

        # Per-symbol
        normalisers = fit_per_symbol_normaliser(t, lengths, sym_ids)
        ps_mean, ps_std = normalisers[0]

        # Pooled (use fit_seq_normaliser)
        dates = pd.DatetimeIndex(pd.bdate_range("2020-01-01", periods=n_rows))
        pseudo = SequenceTensor(
            symbol="_pooled", tensor=t, lengths=lengths, dates=dates,
            feature_names=tuple(f"f{i}" for i in range(n_feat)),
        )
        pool_mean, pool_std = fit_seq_normaliser(pseudo, dates)

        torch.testing.assert_close(ps_mean, pool_mean, atol=1e-5, rtol=1e-5)
        torch.testing.assert_close(ps_std, pool_std, atol=1e-5, rtol=1e-5)

    def test_apply_preserves_padding(self):
        """Normalised tensor must retain zeros beyond lengths."""
        from volforecast.pipeline.norm import apply_per_symbol_normaliser

        n_rows = 10
        max_bars = 20
        n_feat = 3
        lengths = torch.randint(5, max_bars, (n_rows,))
        t = torch.randn(n_rows, max_bars, n_feat)
        # Zero-out pad positions
        for i in range(n_rows):
            t[i, lengths[i] :] = 0.0
        sym_ids = torch.zeros(n_rows, dtype=torch.long)

        normalisers = {0: (torch.ones(n_feat), torch.ones(n_feat) * 2.0)}
        normed = apply_per_symbol_normaliser(t, lengths, sym_ids, normalisers)

        for i in range(n_rows):
            pad_region = normed[i, lengths[i] :]
            assert (pad_region == 0.0).all(), f"Row {i}: pad region is not zero"

    def test_uses_only_own_symbol_rows(self):
        """Each symbol's normaliser must be fit on ONLY that symbol's rows."""
        from volforecast.pipeline.norm import fit_per_symbol_normaliser

        n_rows = 200
        max_bars = 10
        n_feat = 1
        t = torch.zeros(n_rows, max_bars, n_feat)
        lengths = torch.full((n_rows,), max_bars, dtype=torch.long)
        sym_ids = torch.zeros(n_rows, dtype=torch.long)

        # Symbol 0: rows 0-99 have value 10.0
        t[:100] = 10.0
        sym_ids[:100] = 0
        # Symbol 1: rows 100-199 have value 0.0
        t[100:] = 0.0
        sym_ids[100:] = 1

        normalisers = fit_per_symbol_normaliser(t, lengths, sym_ids)
        mean0, _ = normalisers[0]
        mean1, _ = normalisers[1]

        # Mean for symbol 0 should be 10, symbol 1 should be 0
        assert mean0.item() == pytest.approx(10.0, abs=1e-5)
        assert mean1.item() == pytest.approx(0.0, abs=1e-5)

    def test_variable_lengths_excluded_from_stats(self):
        """Padded positions (beyond lengths) must not affect normaliser stats."""
        from volforecast.pipeline.norm import fit_per_symbol_normaliser

        n_rows = 10
        max_bars = 20
        n_feat = 1
        lengths = torch.full((n_rows,), 5, dtype=torch.long)  # Only first 5 bars valid
        t = torch.zeros(n_rows, max_bars, n_feat)
        # Valid region: value 3.0
        t[:, :5, :] = 3.0
        # Pad region: value 999 (should be ignored)
        t[:, 5:, :] = 999.0
        sym_ids = torch.zeros(n_rows, dtype=torch.long)

        normalisers = fit_per_symbol_normaliser(t, lengths, sym_ids)
        mean0, std0 = normalisers[0]
        # Mean should be 3.0 (not contaminated by 999)
        assert mean0.item() == pytest.approx(3.0, abs=1e-5)
        # Std should be ~0 (clamped to eps)
        assert std0.item() < 0.01

    def test_apply_correct_normalisation(self):
        """apply_per_symbol_normaliser should z-score each symbol separately."""
        from volforecast.pipeline.norm import apply_per_symbol_normaliser

        n_rows = 4
        max_bars = 5
        n_feat = 1
        t = torch.zeros(n_rows, max_bars, n_feat)
        lengths = torch.full((n_rows,), max_bars, dtype=torch.long)
        sym_ids = torch.tensor([0, 0, 1, 1])

        t[0] = 10.0
        t[1] = 12.0
        t[2] = 0.0
        t[3] = 4.0

        # sym 0: mean=11, std=1 → row0=(10-11)/1=-1, row1=(12-11)/1=1
        # sym 1: mean=2, std=2 → row2=(0-2)/2=-1, row3=(4-2)/2=1
        normalisers = {
            0: (torch.tensor([11.0]), torch.tensor([1.0])),
            1: (torch.tensor([2.0]), torch.tensor([2.0])),
        }
        normed = apply_per_symbol_normaliser(t, lengths, sym_ids, normalisers)
        assert normed[0, 0, 0].item() == pytest.approx(-1.0)
        assert normed[1, 0, 0].item() == pytest.approx(1.0)
        assert normed[2, 0, 0].item() == pytest.approx(-1.0)
        assert normed[3, 0, 0].item() == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Phase 2.7: Runner integration tests (end-to-end norm_mode threading
# and feature_stack guard).
# ---------------------------------------------------------------------------


def _make_seq_panel(
    symbols: list[str],
    n_days: int,
    *,
    seed: int = 0,
) -> dict[str, pd.DataFrame]:
    """Per-symbol daily RV panel mirroring test_runner_sequences fixture."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2022-01-03", periods=n_days)
    out: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        rv = np.exp(-4.0 + 0.3 * rng.standard_normal(n_days))
        out[sym] = pd.DataFrame({"rv": rv}, index=dates)
    return out


def _write_seq_parquets(
    sequences_dir,
    panel: dict[str, pd.DataFrame],
    *,
    bars_per_day: int = 6,
    feature_cols: tuple[str, ...] = ("buy_vol", "sell_vol", "net_flow"),
    seed: int = 1,
    sym_value_overrides: dict[str, dict[pd.Timestamp, float]] | None = None,
) -> None:
    """Write per-symbol intraday parquets. ``sym_value_overrides`` lets a
    caller force constant feature values on specific (symbol, date) pairs —
    used by the leakage test to inject extreme stats on test dates.
    """
    rng = np.random.default_rng(seed)
    sequences_dir.mkdir(parents=True, exist_ok=True)
    overrides = sym_value_overrides or {}
    for sym, df in panel.items():
        sym_over = overrides.get(sym, {})
        rows = []
        for d in df.index:
            forced = sym_over.get(d)
            for b in range(bars_per_day):
                if forced is not None:
                    vals = np.full(len(feature_cols), float(forced), dtype=np.float32)
                else:
                    vals = rng.standard_normal(len(feature_cols)).astype(np.float32)
                row = {"date": d.strftime("%Y-%m-%d"), "bar_idx": b}
                for col, v in zip(feature_cols, vals):
                    row[col] = float(v)
                rows.append(row)
        pd.DataFrame(rows).to_parquet(sequences_dir / f"{sym}.parquet", index=False)


class TestRunnerPerSymbolNormIntegration:
    """End-to-end runner tests for ``sequences.norm_mode='per_symbol'`` (Phase 2.7)."""

    def test_per_symbol_norm_e2e_smoke(self, tmp_path):
        """LSTM pipeline runs under per_symbol norm and produces finite QLIKE."""
        # Imports kept local so the rest of the module stays import-light.
        from volforecast.config import (
            CVConfig,
            ExperimentConfig,
            ModelConfig,
        )
        from volforecast.pipeline.runner import Pipeline

        panel = _make_seq_panel(["SPY", "AAPL"], n_days=60, seed=11)
        sequences_dir = tmp_path / "sequences"
        cache_dir = tmp_path / "seqcache"
        _write_seq_parquets(sequences_dir, panel)

        cfg = ExperimentConfig(
            name="t_per_symbol_smoke",
            universe=["SPY", "AAPL"],
            date_range=("2022-01-03", "2022-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(
                name="lstm",
                params={
                    "input_dim": 3,
                    "hidden_dim": 8,
                    "n_layers": 1,
                    "dropout": 0.0,
                    "max_epochs": 2,
                    "batch_size": 32,
                    "device": "cpu",
                    "val_fraction": 0.0,
                    "early_stopping_rounds": 0,
                    "loss": "qlike",
                    "seed": 7,
                },
            ),
            cv=CVConfig(
                method="expanding_window",
                train_size=20,
                test_size=20,
                purge_gap=1,
            ),
            sequences={
                "features": ["buy_vol", "sell_vol", "net_flow"],
                "max_bars": 6,
                "sequences_dir": str(sequences_dir),
                "cache_dir": str(cache_dir),
                "norm_mode": "per_symbol",
            },
            fold_cache_enabled=False,
        )

        # Hook the per-symbol normaliser fit so we can compare runner stats to
        # a direct invocation on the same training tensors.
        from volforecast.pipeline import norm as _norm_mod

        captured: dict[str, object] = {}
        original_fit = _norm_mod.fit_per_symbol_normaliser

        def _recording_fit(t, L, sids, **kw):
            out = original_fit(t, L, sids, **kw)
            captured.setdefault("calls", []).append(
                (t.detach().clone(), L.detach().clone(), sids.detach().clone(), out)
            )
            return out

        import volforecast.pipeline.runner as _runner_mod

        # Patch the symbol the runner re-imports inside the fold loop.
        _norm_mod.fit_per_symbol_normaliser = _recording_fit
        try:
            results = Pipeline(cfg).run_pooled(panel)
        finally:
            _norm_mod.fit_per_symbol_normaliser = original_fit
            # Defensive: also clear any reference held on the runner module.
            if hasattr(_runner_mod, "fit_per_symbol_normaliser"):
                _runner_mod.fit_per_symbol_normaliser = original_fit

        # Pipeline completed and returned the standard contract.
        assert 1 in results
        for key in ("metrics", "predictions", "actuals", "model", "duan_correction"):
            assert key in results[1], f"missing key {key!r} in result"
        assert np.isfinite(results[1]["metrics"]["qlike"])
        assert results[1]["predictions"].notna().all()

        # Per-symbol fit was invoked at least once (one per fold).
        assert "calls" in captured and len(captured["calls"]) >= 1
        # Each recorded fit matches a fresh direct call on the same inputs.
        for t_arg, L_arg, sids_arg, stats in captured["calls"]:
            direct = original_fit(t_arg, L_arg, sids_arg)
            assert set(direct.keys()) == set(stats.keys())
            for sid in direct:
                d_mean, d_std = direct[sid]
                r_mean, r_std = stats[sid]
                torch.testing.assert_close(r_mean, d_mean, atol=1e-6, rtol=1e-6)
                torch.testing.assert_close(r_std, d_std, atol=1e-6, rtol=1e-6)

    def test_feature_stack_rejects_per_symbol_norm(self, tmp_path):
        """Construction-time guard: feature_stack + per_symbol must raise."""
        from volforecast.config import (
            CVConfig,
            ExperimentConfig,
            FeatureStackConfig,
            ModelConfig,
            SequenceConfig,
        )

        with pytest.raises(ValueError) as exc_info:
            ExperimentConfig(
                name="t_fs_guard",
                universe=["SPY"],
                date_range=("2022-01-03", "2022-12-31"),
                horizons=[1],
                feature_layers=["har_core"],
                model=ModelConfig(name="lightgbm", params={}),
                cv=CVConfig(method="expanding_window", train_size=80, test_size=20),
                sequences=SequenceConfig(norm_mode="per_symbol"),
                feature_stack=FeatureStackConfig(source_model="lstm"),
            )

        msg = str(exc_info.value)
        assert "feature_stack" in msg, f"guard message missing 'feature_stack': {msg!r}"
        assert "norm_mode" in msg, f"guard message missing 'norm_mode': {msg!r}"
        assert "Phase 3.12" in msg or "not yet supported" in msg, (
            f"guard message must reference Phase 3.12 or 'not yet supported': {msg!r}"
        )

    def test_per_symbol_norm_train_only_leakage(self, tmp_path):
        """Per-symbol stats must be fit on train rows only, never test dates."""
        from volforecast.config import (
            CVConfig,
            ExperimentConfig,
            ModelConfig,
        )
        from volforecast.pipeline.runner import Pipeline

        # 10 dates × 2 symbols. SPY's last 3 dates are forced to value 100.0
        # for every bar → if the normaliser sees those rows, its per-symbol
        # mean for SPY explodes.
        panel = _make_seq_panel(["SPY", "AAPL"], n_days=10, seed=11)
        dates = panel["SPY"].index
        leak_dates = list(dates[-3:])
        sequences_dir = tmp_path / "sequences"
        cache_dir = tmp_path / "seqcache"
        _write_seq_parquets(
            sequences_dir,
            panel,
            sym_value_overrides={"SPY": {d: 100.0 for d in leak_dates}},
        )

        # Patch the registered _fake_seq model from test_runner_sequences if
        # available; otherwise use the lightest real LSTM config so the
        # pipeline produces a single fold.
        # We choose the real LSTM (cpu, tiny) to avoid cross-file test deps.
        cfg = ExperimentConfig(
            name="t_per_symbol_leak",
            universe=["SPY", "AAPL"],
            date_range=("2022-01-03", "2022-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(
                name="lstm",
                params={
                    "input_dim": 3,
                    "hidden_dim": 4,
                    "n_layers": 1,
                    "dropout": 0.0,
                    "max_epochs": 1,
                    "batch_size": 16,
                    "device": "cpu",
                    "val_fraction": 0.0,
                    "early_stopping_rounds": 0,
                    "loss": "qlike",
                    "seed": 7,
                },
            ),
            cv=CVConfig(
                method="expanding_window",
                train_size=7,
                test_size=3,
                purge_gap=0,
            ),
            sequences={
                "features": ["buy_vol", "sell_vol", "net_flow"],
                "max_bars": 6,
                "sequences_dir": str(sequences_dir),
                "cache_dir": str(cache_dir),
                "norm_mode": "per_symbol",
            },
            fold_cache_enabled=False,
        )

        from volforecast.pipeline import norm as _norm_mod

        captured: list[dict[int, tuple[torch.Tensor, torch.Tensor]]] = []
        original_fit = _norm_mod.fit_per_symbol_normaliser

        def _recording_fit(t, L, sids, **kw):
            stats = original_fit(t, L, sids, **kw)
            captured.append(stats)
            return stats

        _norm_mod.fit_per_symbol_normaliser = _recording_fit
        try:
            Pipeline(cfg).run_pooled(panel)
        finally:
            _norm_mod.fit_per_symbol_normaliser = original_fit

        # Exactly one fold ⇒ exactly one normaliser fit.
        assert len(captured) == 1, f"expected 1 fold fit, got {len(captured)}"
        stats = captured[0]
        # Both symbols present in the per-symbol normaliser.
        assert len(stats) == 2

        # For the SPY (whichever symbol_id it received), the per-symbol means
        # must reflect ONLY the first 7 dates (std normal), not the leaked
        # value 100.0. If leakage occurred, mean would be ~30 (3/10 * 100).
        max_abs_mean = max(float(mean.abs().max().item()) for mean, _ in stats.values())
        assert max_abs_mean < 5.0, (
            f"per-symbol mean magnitude {max_abs_mean:.2f} suggests leakage of "
            "post-train rows into the normaliser fit"
        )
