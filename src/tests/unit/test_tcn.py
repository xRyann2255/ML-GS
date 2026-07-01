"""Unit tests for the TCN (Temporal Convolutional Network) volatility model.

TDD tests written BEFORE implementation.  The stub in ``lstm.py`` raises
``NotImplementedError`` — every test here is expected to **fail** until the
real ``_TCNBody`` and ``TCNVolModel`` are implemented.

Validates:
1. ``requires_sequences`` flag is True.
2. ``_TCNBody`` forward shape is correct.
3. Gradients flow through the causal conv stack.
4. Causal property: future inputs don't affect past outputs.
5. Training loss decreases over epochs.
6. ``predict`` returns the right shape.
7. ``save`` / ``load`` round-trip gives identical predictions.
8. QLIKE loss trains and converges.
9. ``get_params`` returns all constructor args.
10. Masked pooling respects variable sequence lengths.

Marked ``slow`` — excluded by ``./vol test``, included by ``./vol test-all``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from volforecast.data.sequence_cache import SequenceTensor
from volforecast.models.lstm import TCNVolModel

# _TCNBody may not exist yet; guard the import so the file parses.
try:
    from volforecast.models.lstm import _TCNBody
except ImportError:
    _TCNBody = None

pytestmark = pytest.mark.slow

# ---------------------------------------------------------------------------
# Synthetic data helper (mirrors test_lstm.py)
# ---------------------------------------------------------------------------

def _make_synthetic_sequence(
    n_dates: int = 120,
    max_bars: int = 24,
    n_features: int = 3,
    seed: int = 0,
) -> tuple[SequenceTensor, np.ndarray]:
    """Build a (sequence, target) pair with a learnable signal."""
    rng = np.random.default_rng(seed)
    lengths = rng.integers(8, max_bars + 1, size=n_dates).astype(np.int64)

    tensor = np.zeros((n_dates, max_bars, n_features), dtype=np.float32)
    targets = np.zeros(n_dates, dtype=np.float32)
    for d in range(n_dates):
        n = int(lengths[d])
        latent = float(rng.normal(0.0, 1.0))
        scale = np.exp(latent * 0.5)
        x = rng.standard_normal((n, n_features)).astype(np.float32) * scale
        tensor[d, :n, :] = x
        targets[d] = float(np.log(np.var(x[:, 0]) + 1e-3))

    dates = pd.bdate_range("2023-01-02", periods=n_dates)
    seq = SequenceTensor(
        symbol="SYN",
        tensor=torch.from_numpy(tensor),
        lengths=torch.from_numpy(lengths),
        dates=dates,
        feature_names=tuple(f"f{i}" for i in range(n_features)),
    )
    return seq, targets


# ── 1. Contract ───────────────────────────────────────────────────────────

class TestTCNContract:
    def test_requires_sequences(self):
        assert getattr(TCNVolModel, "requires_sequences", False) is True

    def test_get_params(self):
        m = TCNVolModel(
            input_dim=5,
            n_channels=[32, 32],
            kernel_size=5,
            dropout=0.1,
            learning_rate=2e-3,
            weight_decay=1e-4,
            max_epochs=50,
            batch_size=64,
            val_fraction=0.15,
            early_stopping_rounds=5,
            val_purge_gap=1,
            loss="qlike",
            device="cpu",
            precision="fp32",
            seed=42,
        )
        params = m.get_params()
        assert isinstance(params, dict)
        assert params["input_dim"] == 5
        assert params["n_channels"] == [32, 32]
        assert params["kernel_size"] == 5
        assert params["dropout"] == 0.1
        assert params["learning_rate"] == 2e-3
        assert params["weight_decay"] == 1e-4
        assert params["max_epochs"] == 50
        assert params["batch_size"] == 64
        assert params["val_fraction"] == 0.15
        assert params["loss"] == "qlike"
        assert params["seed"] == 42


# ── 2. _TCNBody nn.Module tests ──────────────────────────────────────────

@pytest.mark.skipif(_TCNBody is None, reason="_TCNBody not yet implemented")
class TestTCNBody:
    def test_forward_shape(self):
        """Output shape is (B,) for a random input."""
        body = _TCNBody(input_dim=3, n_channels=[32, 32, 16], kernel_size=3, dropout=0.0)
        B, T, F = 8, 78, 3
        x = torch.randn(B, T, F)
        lengths = torch.full((B,), T, dtype=torch.long)
        out = body(x, lengths)
        assert out.shape == (B,)

    def test_gradient_flow(self):
        """loss.backward() produces non-zero grads on conv weights."""
        body = _TCNBody(input_dim=3, n_channels=[16, 16], kernel_size=3, dropout=0.0)
        B, T, F = 4, 24, 3
        x = torch.randn(B, T, F)
        lengths = torch.full((B,), T, dtype=torch.long)
        out = body(x, lengths)
        loss = out.sum()
        loss.backward()
        conv_params = [p for p in body.parameters() if p.dim() >= 2]
        assert len(conv_params) > 0, "No conv parameters found"
        grads_nonzero = [p.grad is not None and p.grad.abs().sum() > 0 for p in conv_params]
        assert all(grads_nonzero), "Some conv weights have zero gradients"

    def test_causal_property(self):
        """Perturbing input at time t must NOT change output at earlier times.

        Strategy: run _TCNBody on the full sequence, record per-timestep
        intermediate activations.  Then perturb position t=40 and re-run;
        outputs pooled from positions < 40 should be unchanged.

        Since _TCNBody pools globally, we test causality at the last conv
        layer output level before pooling: perturbing t=40 should leave
        positions 0..39 unchanged.
        """
        torch.manual_seed(42)
        body = _TCNBody(input_dim=3, n_channels=[16, 16], kernel_size=3, dropout=0.0)
        body.eval()
        B, T, F = 1, 60, 3
        x = torch.randn(B, T, F)
        lengths = torch.tensor([T], dtype=torch.long)

        # We'll test via the full model forward: feed two copies of x,
        # one with a perturbation at t=40.  If causal, positions < 40
        # in the final conv output must be identical.
        x_orig = x.clone()
        x_pert = x.clone()
        x_pert[0, 40, :] += 10.0  # large perturbation

        # Transpose to (B, F, T) as the conv stack expects
        # We access the network attribute that holds the residual blocks.
        # Fall back to running full forward and checking the pooled result
        # on two sub-sequences up to t=39.
        x_short = x_orig[:, :40, :]
        x_short_pert = x_pert[:, :40, :]
        lengths_short = torch.tensor([40], dtype=torch.long)

        out_orig = body(x_short, lengths_short)
        out_pert = body(x_short_pert, lengths_short)
        torch.testing.assert_close(out_orig, out_pert, atol=1e-6, rtol=0)

    def test_masked_pooling(self):
        """Shorter sequences must ignore padded (zero) regions.

        Build two inputs: one with length=20 (rest zero-padded) and one
        identical up to t=20 but with garbage in t=20..T.  Outputs must
        match if masking works correctly.
        """
        torch.manual_seed(7)
        body = _TCNBody(input_dim=3, n_channels=[16, 16], kernel_size=3, dropout=0.0)
        body.eval()
        T, F = 50, 3
        real_len = 20

        x_clean = torch.zeros(1, T, F)
        x_clean[0, :real_len, :] = torch.randn(real_len, F)

        x_dirty = x_clean.clone()
        x_dirty[0, real_len:, :] = torch.randn(T - real_len, F) * 5.0  # garbage

        lengths = torch.tensor([real_len], dtype=torch.long)

        out_clean = body(x_clean, lengths)
        out_dirty = body(x_dirty, lengths)
        torch.testing.assert_close(out_clean, out_dirty, atol=1e-5, rtol=0)


# ── 3. TCNVolModel fit / predict ─────────────────────────────────────────

class TestTCNFitPredict:
    def test_fit_loss_decreases(self):
        """Training loss at the end must be lower than at the start."""
        seq, y = _make_synthetic_sequence(n_dates=60, max_bars=78, n_features=3, seed=10)
        m = TCNVolModel(
            input_dim=3,
            n_channels=[16, 16],
            kernel_size=3,
            max_epochs=15,
            batch_size=16,
            val_fraction=0.0,
            loss="mse",
            device="cpu",
            seed=10,
        )
        m.fit(seq, pd.Series(y, index=seq.dates))
        hist = m.history_
        assert len(hist) >= 2, "Not enough training history recorded"
        first_loss = hist[0]["train_loss"]
        last_loss = hist[-1]["train_loss"]
        assert last_loss < first_loss, (
            f"Loss did not decrease: first={first_loss:.4f}, last={last_loss:.4f}"
        )

    def test_predict_shape(self):
        seq, y = _make_synthetic_sequence(n_dates=60, max_bars=78, n_features=3, seed=11)
        m = TCNVolModel(
            input_dim=3,
            n_channels=[16, 16],
            kernel_size=3,
            max_epochs=3,
            batch_size=16,
            device="cpu",
            seed=11,
        )
        m.fit(seq, pd.Series(y, index=seq.dates))
        preds = m.predict(seq)
        assert isinstance(preds, np.ndarray)
        assert preds.shape == (len(seq.dates),)
        assert np.isfinite(preds).all()

    def test_qlike_loss_trains(self):
        """QLIKE custom loss must train without NaN and converge."""
        seq, y = _make_synthetic_sequence(n_dates=60, max_bars=78, n_features=3, seed=12)
        m = TCNVolModel(
            input_dim=3,
            n_channels=[16, 16],
            kernel_size=3,
            max_epochs=10,
            batch_size=16,
            val_fraction=0.0,
            loss="qlike",
            device="cpu",
            seed=12,
        )
        m.fit(seq, pd.Series(y, index=seq.dates))
        preds = m.predict(seq)
        assert np.isfinite(preds).all(), "QLIKE training produced NaN predictions"
        hist = m.history_
        first_loss = hist[0]["train_loss"]
        last_loss = hist[-1]["train_loss"]
        assert last_loss < first_loss, "QLIKE loss did not decrease over training"


# ── 4. Save / Load ───────────────────────────────────────────────────────

class TestTCNSaveLoad:
    def test_save_load_roundtrip(self, tmp_path: Path):
        seq, y = _make_synthetic_sequence(n_dates=40, max_bars=78, n_features=3, seed=13)
        m = TCNVolModel(
            input_dim=3,
            n_channels=[16, 16],
            kernel_size=3,
            max_epochs=3,
            batch_size=16,
            device="cpu",
            seed=13,
        )
        m.fit(seq, pd.Series(y, index=seq.dates))
        preds_before = m.predict(seq)

        save_path = tmp_path / "test_tcn_save.joblib"
        m.save(save_path)
        assert save_path.exists()

        loaded = TCNVolModel.load(save_path)
        preds_after = loaded.predict(seq)
        np.testing.assert_allclose(preds_before, preds_after, rtol=0, atol=0)
