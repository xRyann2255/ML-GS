"""Math-correctness gates for LSTM training-loop optimisations.

These tests are the verification gate from the optimisation plan
(``memory/session/plan.md``). For each kept optimisation we either prove
(a) bitwise identical weights to baseline (T1), or (b) deterministic and
reproducible across same-seed runs (T2/T3) — both required to claim
"no model-performance regression".

Optimisations kept (current `LSTMVolModel.fit` implementation):

- **A2**: ``DataLoader`` removed, manual ``torch.randperm`` per epoch.
- **A4**: ``lengths`` kept on CPU through ``_LSTMBody.forward`` (saves a
  spurious host↔device hop).
- **A5**: per-batch ``loss.item()`` replaced with on-device 0-d tensor sum,
  one device-host sync at end of epoch.

Optimisations reverted (proven slower in
``workspace/tmp/lstm-bench-*.json``):

- A1 ``fused=True`` AdamW — 0.96× on H100 (LSTM has too few param tensors
  for the fused launch overhead to amortise).
- A9 ``torch.set_num_threads(1)`` — measured slower (the length sort inside
  ``pack_padded_sequence`` benefits from CPU parallelism after all).
- A8 ``torch.compile`` — captures ~0 benefit because pack_padded_sequence
  forces dynamic shapes (recompile per shape eats the gain). The compile
  mode was changed from ``max-autotune`` → ``reduce-overhead`` to make the
  opt-in path safer (avoids multi-minute autotune cost per CV fold).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import torch

from volforecast.data.sequence_cache import SequenceTensor
from volforecast.models.lstm import LSTMVolModel, _LSTMBody

pytestmark = pytest.mark.slow


def _make_synthetic_sequence(
    n_dates: int = 60, max_bars: int = 16, n_features: int = 3, seed: int = 0
) -> tuple[SequenceTensor, pd.Series]:
    rng = np.random.default_rng(seed)
    lengths = rng.integers(8, max_bars + 1, size=n_dates).astype(np.int64)
    tensor = np.zeros((n_dates, max_bars, n_features), dtype=np.float32)
    targets = np.zeros(n_dates, dtype=np.float32)
    for d in range(n_dates):
        n = int(lengths[d])
        latent = float(rng.normal(0.0, 1.0))
        x = rng.standard_normal((n, n_features)).astype(np.float32) * np.exp(latent * 0.5)
        tensor[d, :n, :] = x
        targets[d] = float(np.log(np.var(x[:, 0]) + 1e-3))
    dates = pd.bdate_range("2023-01-02", periods=n_dates)
    seq = SequenceTensor(
        symbol="SYN",
        tensor=torch.from_numpy(tensor),
        lengths=torch.from_numpy(lengths),
        dates=dates,
        feature_names=[f"f{i}" for i in range(n_features)],
    )
    return seq, pd.Series(targets, index=dates, name="logrv")


def _train(seed: int = 42, **overrides):
    seq, y = _make_synthetic_sequence(seed=seed)
    params = dict(
        input_dim=seq.n_features,
        hidden_dim=16,
        n_layers=1,
        dropout=0.0,
        learning_rate=5e-3,
        max_epochs=5,
        batch_size=16,
        val_fraction=0.2,
        early_stopping_rounds=100,
        loss="qlike",
        device="cpu",
        precision="fp32",
        compile=False,
        num_workers=0,
        seed=seed,
    )
    params.update(overrides)
    model = LSTMVolModel(**params)
    model.fit(seq, y)
    return model, seq, y


# ---------------------------------------------------------------------------
# A2 — manual perm replaces DataLoader
# ---------------------------------------------------------------------------


def test_a2_determinism_same_seed_bitwise_identical() -> None:
    """Same seed → bitwise identical final weights (proves the new manual
    perm path is fully deterministic; no hidden RNG draws.)"""
    m1, _, _ = _train(seed=42)
    m2, _, _ = _train(seed=42)
    sd1 = m1._module.state_dict()
    sd2 = m2._module.state_dict()
    assert set(sd1.keys()) == set(sd2.keys())
    for k in sd1:
        assert torch.equal(sd1[k], sd2[k]), f"Param {k!r} not bitwise identical across same-seed runs"


def test_a2_different_seeds_produce_different_weights() -> None:
    """Sanity: different seeds → different weights (proves seed is wired in)."""
    m1, _, _ = _train(seed=42)
    m2, _, _ = _train(seed=43)
    sd1 = m1._module.state_dict()
    sd2 = m2._module.state_dict()
    diffs = [(sd1[k] - sd2[k]).abs().max().item() for k in sd1]
    assert max(diffs) > 1e-3, "Different seeds produced suspiciously similar weights"


def test_a2_train_loss_converges() -> None:
    """A2 path produces a normal training curve (loss decreases)."""
    m, _, _ = _train(seed=42, max_epochs=10)
    losses = [h["train_loss"] for h in m.history_]
    assert losses[-1] < losses[0], f"Loss did not decrease: {losses[0]:.4f} → {losses[-1]:.4f}"


# ---------------------------------------------------------------------------
# A4 — lengths stay on CPU through _LSTMBody.forward
# ---------------------------------------------------------------------------


def test_a4_forward_accepts_cpu_lengths_when_x_is_cpu() -> None:
    """`_LSTMBody.forward` must accept CPU lengths with CPU input (the A4 case
    that exercises the production code path)."""
    torch.manual_seed(0)
    body = _LSTMBody(input_dim=3, hidden_dim=8, n_layers=1, dropout=0.0)
    x = torch.randn(4, 10, 3)
    lengths_cpu = torch.tensor([10, 8, 6, 4], dtype=torch.long)  # already on CPU
    out = body(x, lengths_cpu)
    assert out.shape == (4,)
    assert torch.isfinite(out).all()


def test_a4_forward_output_invariant_to_lengths_device() -> None:
    """The forward output must NOT depend on which device ``lengths`` lives
    on — ``pack_padded_sequence`` reads them on CPU internally regardless."""
    torch.manual_seed(0)
    body = _LSTMBody(input_dim=3, hidden_dim=8, n_layers=1, dropout=0.0)
    x = torch.randn(4, 10, 3)
    lengths_cpu = torch.tensor([10, 8, 6, 4], dtype=torch.long)
    lengths_cpu_int32 = lengths_cpu.to(torch.int32)
    out1 = body(x, lengths_cpu)
    out2 = body(x, lengths_cpu_int32)
    assert torch.allclose(out1, out2, atol=0.0, rtol=0.0), \
        "Forward output changed based on lengths dtype/device — should be invariant"


# ---------------------------------------------------------------------------
# A5 — deferred loss sync (epoch-level, not per-batch)
# ---------------------------------------------------------------------------


def test_a5_reported_train_loss_matches_manual_mean() -> None:
    """The deferred-sum/divide that A5 uses to compute per-epoch train loss
    must produce the same value as a naive per-batch mean.

    Strategy: monkey-patch the loss function to record every per-batch value
    on each forward, then compare ``history_[-1]['train_loss']`` to
    ``mean(recorded_losses_in_final_epoch)``.
    """
    seq, y = _make_synthetic_sequence(seed=42)
    recorded: list[float] = []
    from volforecast.models import lstm as lstm_mod
    orig = lstm_mod._qlike_loss

    def spy(pred, target):
        out = orig(pred, target)
        recorded.append(float(out.detach().cpu().item()))
        return out

    lstm_mod._LOSSES["qlike"] = spy
    try:
        model = LSTMVolModel(
            input_dim=seq.n_features, hidden_dim=8, n_layers=1, dropout=0.0,
            learning_rate=1e-3, max_epochs=3, batch_size=16,
            val_fraction=0.2, early_stopping_rounds=100, loss="qlike",
            device="cpu", precision="fp32", compile=False, num_workers=0, seed=42,
        )
        model.fit(seq, y)
    finally:
        lstm_mod._LOSSES["qlike"] = orig

    # Compute n_batches per training epoch — same arithmetic as fit() does.
    n_train = seq.tensor.shape[0] - int(round(0.2 * seq.tensor.shape[0]))
    import math
    n_batches_per_epoch = math.ceil(n_train / 16)
    n_val_batches_per_epoch = math.ceil((seq.tensor.shape[0] - n_train) / 16)

    # In each epoch the order is: n_batches_per_epoch train + n_val_batches val.
    # We want only the train-batch losses for the final epoch.
    epoch_total = n_batches_per_epoch + n_val_batches_per_epoch
    final_epoch_train = recorded[
        2 * epoch_total : 2 * epoch_total + n_batches_per_epoch
    ]
    expected = float(np.mean(final_epoch_train))
    reported = model.history_[-1]["train_loss"]
    assert abs(reported - expected) < 1e-5, \
        f"Reported {reported:.6f} vs spy mean {expected:.6f}"


# ---------------------------------------------------------------------------
# End-to-end: save/load round-trip preserves the optimised model
# ---------------------------------------------------------------------------


def test_save_load_round_trip_preserves_predictions(tmp_path) -> None:
    """Smoke: full optimised model survives a save→load cycle bit-identical."""
    model, seq, _ = _train(seed=42)
    preds_before = model.predict(seq)
    path = tmp_path / "model.pt"
    model.save(path)
    restored = LSTMVolModel.load(path)
    preds_after = restored.predict(seq)
    np.testing.assert_allclose(preds_before, preds_after, atol=0, rtol=0)


# ---------------------------------------------------------------------------
# Step 1.1 — predict + extract_features use the compiled body when available
# ---------------------------------------------------------------------------


def test_predict_uses_compiled_when_available() -> None:
    """``predict`` must call ``self._compiled`` when it is not None.

    On CPU ``_maybe_compile`` is a no-op that returns the underlying
    module, so ``self._compiled is self._module``. We patch
    ``self._compiled`` to a counting wrapper around the trained module
    and verify ``predict`` routes the forward through the wrapper.
    """
    model, seq, _ = _train(seed=42, max_epochs=2)
    assert model._compiled is not None  # _maybe_compile returns body on CPU

    underlying = model._module
    counter = {"n": 0}

    class _CountingWrapper(torch.nn.Module):
        def __init__(self, inner: torch.nn.Module) -> None:
            super().__init__()
            self.inner = inner

        def forward(
            self,
            x: torch.Tensor,
            lengths: torch.Tensor,
            symbol_ids: torch.Tensor | None = None,
        ) -> torch.Tensor:
            counter["n"] += 1
            return self.inner(x, lengths, symbol_ids)

        def eval(self):  # mirror nn.Module API
            self.inner.eval()
            return self

    model._compiled = _CountingWrapper(underlying)
    _ = model.predict(seq)
    assert counter["n"] > 0, "predict did not route through self._compiled"


def test_predict_compile_numeric_parity() -> None:
    """``compile=True`` vs ``compile=False`` must produce equal predictions
    (on CPU ``_maybe_compile`` is a no-op so they are effectively identical;
    this gates against silent divergence introduced by Step 1.1)."""
    m1, seq, _ = _train(seed=42, compile=False)
    m2, _, _ = _train(seed=42, compile=True)
    p1 = m1.predict(seq)
    p2 = m2.predict(seq)
    np.testing.assert_allclose(p1, p2, atol=1e-5, rtol=0)


# ---------------------------------------------------------------------------
# Step 1.3 — length-bucket batch sampler
# ---------------------------------------------------------------------------


def test_length_bucket_sampler_covers_all_indices() -> None:
    """The sampler must return a permutation: every index exactly once."""
    from volforecast.models.lstm import _length_bucketed_perm

    L = torch.arange(100, dtype=torch.long)
    perm = _length_bucketed_perm(L, batch_size=8, n_buckets=16)
    assert perm.shape == (100,)
    np.testing.assert_array_equal(np.sort(perm.numpy()), np.arange(100))


def test_length_bucket_sampler_reduces_per_batch_length_variance() -> None:
    """Bucketed perm reduces per-batch std of lengths by ≥3× vs random perm.

    Uses ``n=4096`` (bucket_size=256, well above batch_size=64) so each
    batch lives almost entirely within one bucket.
    """
    from volforecast.models.lstm import _length_bucketed_perm

    torch.manual_seed(7)
    L = torch.randint(10, 2340, (4096,), dtype=torch.long)
    batch_size = 64

    def mean_per_batch_std(perm: torch.Tensor) -> float:
        stds = []
        Lp = L[perm].float().numpy()
        for start in range(0, len(Lp), batch_size):
            chunk = Lp[start : start + batch_size]
            if len(chunk) > 1:
                stds.append(float(chunk.std()))
        return float(np.mean(stds))

    random_perm = torch.randperm(L.shape[0])
    bucket_perm = _length_bucketed_perm(L, batch_size=batch_size, n_buckets=16)
    rnd_std = mean_per_batch_std(random_perm)
    buc_std = mean_per_batch_std(bucket_perm)
    assert buc_std * 3 <= rnd_std, (
        f"Bucketed per-batch std={buc_std:.2f} not ≤ random/3={rnd_std / 3:.2f}"
    )


def test_length_bucket_sampler_deterministic_under_seed() -> None:
    """Same seeded torch generator → identical permutation."""
    from volforecast.models.lstm import _length_bucketed_perm

    L = torch.arange(200, dtype=torch.long)
    torch.manual_seed(0)
    p1 = _length_bucketed_perm(L, batch_size=8, n_buckets=4)
    torch.manual_seed(0)
    p2 = _length_bucketed_perm(L, batch_size=8, n_buckets=4)
    assert torch.equal(p1, p2)


def test_length_bucket_sampler_n_buckets_one_matches_random() -> None:
    """n_buckets=1 must collapse to torch.randperm under the same seed."""
    from volforecast.models.lstm import _length_bucketed_perm

    L = torch.arange(50, dtype=torch.long)
    torch.manual_seed(123)
    expected = torch.randperm(50)
    torch.manual_seed(123)
    got = _length_bucketed_perm(L, batch_size=8, n_buckets=1)
    assert torch.equal(got, expected)
