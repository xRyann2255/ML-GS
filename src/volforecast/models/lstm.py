"""LSTM volatility model — sequence-first PyTorch implementation.

Sequence-first contract: ``fit`` and ``predict`` receive a
:class:`volforecast.data.sequence_cache.SequenceTensor` (cached padded
``(n_dates, max_bars, n_features)`` tensors with valid-length info), not a
DataFrame. The runner is responsible for dispatching on
``LSTMVolModel.requires_sequences``.

Architecture
------------
masked LSTM (``pack_padded_sequence``) → attention pool → 2-layer MLP head →
scalar log-RV.

Training
--------
- AdamW + ReduceLROnPlateau.
- Optional MSE or QLIKE loss in log-RV space (QLIKE matches the LightGBM
  custom objective so the loss is comparable across model classes).
- Optional validation tail with early stopping (``val_fraction`` /
  ``early_stopping_rounds``).
- Device: ``'auto'`` (cuda → mps → cpu) for portability. On NVIDIA H100 the
  forward/backward pass auto-enables TF32, bf16 autocast, and
  ``torch.compile(mode='max-autotune')``; all no-ops on CPU so the same code
  path runs locally.

This module is registered as ``lstm`` in the model registry so a config of
``model.name: lstm`` routes here through the runner's sequence dispatch.

The ``TCNVolModel`` at the bottom of this file provides a TCN alternative
using dilated causal convolutions with an identical fit/predict API.
"""

from __future__ import annotations

import logging
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence

from volforecast.data.sequence_cache import SequenceTensor
from volforecast.models._base import _BaseModel
from volforecast.registry import register_model

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Device + precision helpers
# ---------------------------------------------------------------------------


def _resolve_device(device: str) -> str:
    """Resolve ``'auto'`` into the best available concrete device.

    Order: cuda > mps > cpu. Explicit names pass through unchanged.
    """
    if device != "auto":
        return device
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _resolve_precision(precision: str, device: str) -> torch.dtype | None:
    """Return autocast dtype, or ``None`` if autocast should be disabled.

    H100 bf16 is the production target; CPU and MPS fall back to no autocast
    so the same code path is safe locally.
    """
    if precision == "fp32" or device == "cpu":
        return None
    if precision == "bf16":
        return torch.bfloat16
    if precision == "fp16":
        return torch.float16
    if precision == "auto":
        if device == "cuda":
            return torch.bfloat16  # H100 native
        return None
    raise ValueError(f"Unknown precision: {precision!r}")


# ---------------------------------------------------------------------------
# Internal nn.Module pieces
# ---------------------------------------------------------------------------


class _AttentionPool(nn.Module):
    """Length-masked additive attention pool over LSTM outputs."""

    def __init__(self, hidden_dim: int) -> None:
        super().__init__()
        self.score = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, h: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """``h`` (B, T, H), ``mask`` (B, T) bool with True=valid. Returns (B, H)."""
        logits = self.score(h).squeeze(-1)  # (B, T)
        logits = logits.masked_fill(~mask, float("-inf"))
        all_invalid = (~mask).all(dim=1, keepdim=True)
        weights = torch.softmax(logits, dim=1)
        weights = torch.where(all_invalid, torch.zeros_like(weights), weights)
        pooled = torch.bmm(weights.unsqueeze(1), h).squeeze(1)
        return pooled

    def forward_with_weights(
        self, h: torch.Tensor, mask: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Like forward but also returns attention weights (B, T)."""
        logits = self.score(h).squeeze(-1)
        logits = logits.masked_fill(~mask, float("-inf"))
        all_invalid = (~mask).all(dim=1, keepdim=True)
        weights = torch.softmax(logits, dim=1)
        weights = torch.where(all_invalid, torch.zeros_like(weights), weights)
        pooled = torch.bmm(weights.unsqueeze(1), h).squeeze(1)
        return pooled, weights


class _LSTMBody(nn.Module):
    """Masked LSTM → pool → head → scalar log-RV."""

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        n_layers: int,
        dropout: float,
        bidirectional: bool = False,
        n_symbols: int = 0,
        symbol_embed_dim: int = 8,
        pool_mode: str = "attention",
        head_mode: str = "mlp",
        context_dim: int = 0,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.n_layers = n_layers
        self.bidirectional = bidirectional
        self.n_symbols = n_symbols
        self.symbol_embed_dim = symbol_embed_dim if (n_symbols > 0 and symbol_embed_dim > 0) else 0
        self.pool_mode = pool_mode
        self.head_mode = head_mode
        self.context_dim = context_dim

        if pool_mode not in ("attention", "last_hidden"):
            raise ValueError(f"Unknown pool_mode {pool_mode!r}; expected 'attention' or 'last_hidden'")
        if head_mode not in ("mlp", "linear"):
            raise ValueError(f"Unknown head_mode {head_mode!r}; expected 'mlp' or 'linear'")

        if self.n_symbols > 0 and self.symbol_embed_dim > 0:
            self.symbol_emb = nn.Embedding(n_symbols, self.symbol_embed_dim)

        lstm_input_dim = input_dim + self.symbol_embed_dim

        self.lstm = nn.LSTM(
            input_size=lstm_input_dim,
            hidden_size=hidden_dim,
            num_layers=n_layers,
            batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0,
            bidirectional=bidirectional,
        )
        out_dim = hidden_dim * (2 if bidirectional else 1)
        head_input_dim = out_dim + context_dim

        if pool_mode == "attention":
            self.pool = _AttentionPool(out_dim)
        # last_hidden: no pool module needed — index final valid timestep

        if head_mode == "mlp":
            self.head = nn.Sequential(
                nn.Linear(head_input_dim, out_dim),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(out_dim, 1),
            )
        else:  # linear
            self.head = nn.Linear(head_input_dim, 1)

    def _encode(self, x: torch.Tensor, lengths: torch.Tensor, symbol_ids: torch.Tensor | None = None):
        """Shared encoder: LSTM + mask. Returns (out, mask)."""
        if self.symbol_embed_dim > 0 and symbol_ids is not None:
            emb = self.symbol_emb(symbol_ids)
            emb_exp = emb.unsqueeze(1).expand(-1, x.shape[1], -1)
            x = torch.cat([x, emb_exp], dim=-1)

        # Pre-sort by descending length so we can use enforce_sorted=True.
        # This avoids pack_padded_sequence's internal sort which produces
        # sorted_indices=None vs Tensor non-determinism that triggers
        # torch.compile recompilation storms.
        lengths_cpu = lengths.cpu().to(torch.int64)
        sorted_len, sort_idx = lengths_cpu.sort(descending=True)
        x_sorted = x.index_select(0, sort_idx.to(x.device))

        packed = pack_padded_sequence(
            x_sorted,
            sorted_len,
            batch_first=True,
            enforce_sorted=True,
        )
        packed_out, _ = self.lstm(packed)
        out_sorted, _ = pad_packed_sequence(packed_out, batch_first=True, total_length=x.shape[1])

        # Unsort back to original batch order.
        unsort_idx = sort_idx.argsort().to(x.device)
        out = out_sorted.index_select(0, unsort_idx)

        arange = torch.arange(x.shape[1], device=x.device).unsqueeze(0)
        mask = arange < lengths.to(x.device).unsqueeze(1)
        return out, mask

    def _pool(self, out: torch.Tensor, mask: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        """Pool LSTM outputs according to pool_mode. Returns (B, H)."""
        if self.pool_mode == "attention":
            return self.pool(out, mask)
        # last_hidden: gather the output at each sequence's last valid timestep
        idx = (lengths.to(out.device) - 1).clamp(min=0).long()  # (B,)
        idx = idx.unsqueeze(1).unsqueeze(2).expand(-1, 1, out.shape[2])  # (B, 1, H)
        pooled = out.gather(1, idx).squeeze(1)  # (B, H)
        return pooled

    def forward(
        self,
        x: torch.Tensor,
        lengths: torch.Tensor,
        symbol_ids: torch.Tensor | None = None,
        context: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """``x`` (B, T, F), ``lengths`` (B,) int, ``symbol_ids`` (B,) int or None.

        Returns (B,) log-RV.

        ``lengths`` is expected to already live on CPU — `pack_padded_sequence`
        requires CPU int64 lengths. The `.cpu()` call is a no-op when
        lengths is already on CPU but guards against DDP Manager-proxy
        deserialization placing it on the current CUDA device.
        """
        out, mask = self._encode(x, lengths, symbol_ids)
        pooled = self._pool(out, mask, lengths)
        if context is not None:
            pooled = torch.cat([pooled, context], dim=-1)
        return self.head(pooled).squeeze(-1)

    def forward_with_internals(
        self,
        x: torch.Tensor,
        lengths: torch.Tensor,
        symbol_ids: torch.Tensor | None = None,
        context: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Like forward but returns (prediction, pooled_embedding, attention_weights).

        Returns
        -------
        prediction : (B,) log-RV
        pooled : (B, H) pooled hidden state before MLP head
        weights : (B, T) attention weights over timesteps (zeros if pool_mode='last_hidden')
        """
        out, mask = self._encode(x, lengths, symbol_ids)
        if self.pool_mode == "attention":
            pooled, weights = self.pool.forward_with_weights(out, mask)
        else:
            pooled = self._pool(out, mask, lengths)
            weights = torch.zeros(out.shape[0], out.shape[1], device=out.device)
        if context is not None:
            pooled = torch.cat([pooled, context], dim=-1)
        prediction = self.head(pooled).squeeze(-1)
        return prediction, pooled, weights


# ---------------------------------------------------------------------------
# Loss functions
# ---------------------------------------------------------------------------


def _mse_loss(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    return torch.mean((pred - target) ** 2)


def _qlike_loss(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """QLIKE in log-RV space.

    For ``y = log(RV)`` and ``y_hat`` a predicted log-RV::

        QLIKE = exp(y - y_hat) - (y - y_hat) - 1

    matches the LightGBM custom objective in
    ``volforecast.models.lightgbm`` so the loss is comparable across models.
    """
    diff = target - pred
    diff = torch.clamp(diff, min=-10.0, max=10.0)
    return torch.mean(torch.exp(diff) - diff - 1.0)


_LOSSES = {"mse": _mse_loss, "qlike": _qlike_loss}


# ---------------------------------------------------------------------------
# Attention feature utilities (used by extract_features)
# ---------------------------------------------------------------------------


def compute_attention_entropy(
    weights: torch.Tensor, mask: torch.Tensor
) -> torch.Tensor:
    """Compute Shannon entropy of attention weights over valid positions.

    Parameters
    ----------
    weights : (B, T) attention weights (sum to 1 over valid positions)
    mask : (B, T) bool, True = valid position

    Returns
    -------
    (B,) entropy values. Entropy of uniform(K) = log(K).
    """
    # Clamp to avoid log(0); masked positions should already be 0-weight
    safe = weights.clamp(min=1e-12)
    # Only sum over valid positions
    log_w = torch.log(safe) * mask.float()
    entropy = -(weights * log_w).sum(dim=1)
    return entropy


def compute_attention_peak_time(
    weights: torch.Tensor, max_bars: int
) -> torch.Tensor:
    """Return normalized position of attention peak (argmax / max_bars).

    Parameters
    ----------
    weights : (B, T) attention weights
    max_bars : int, normalization denominator

    Returns
    -------
    (B,) peak position in [0, 1].
    """
    peak_idx = weights.argmax(dim=1).float()
    return peak_idx / max(max_bars - 1, 1)


# ---------------------------------------------------------------------------
# Train/val split helpers
# ---------------------------------------------------------------------------


def _split_train_val_by_date(
    dates: np.ndarray, val_fraction: float
) -> tuple[np.ndarray, np.ndarray]:
    """Split row indices into (train, val) by UNIQUE DATES, val = last N dates.

    Pooled training has multiple symbols per date. A row-count split would
    place some symbols of the same date in train and others in val,
    leaking signal across the early-stopping boundary. This helper splits
    on unique dates so every row of a given date lives in the same side.

    Parameters
    ----------
    dates : np.ndarray
        Per-row date values (any dtype that ``np.unique`` accepts).
        Typically the result of ``seq.dates[finite_mask]``.
    val_fraction : float
        Fraction of UNIQUE dates to assign to val (taken from the tail).

    Returns
    -------
    train_idx, val_idx : np.ndarray
        Row indices into ``dates``. ``np.concatenate([train_idx, val_idx])``
        is NOT necessarily sorted — the caller should treat them as masks.
        When ``val_fraction == 0`` or rounds to zero dates, ``val_idx`` is
        empty. When ``val_fraction`` rounds to all unique dates,
        ``train_idx`` is empty (caller is expected to fall through to
        no-val behaviour in that degenerate case).
    """
    n = dates.shape[0]
    if n == 0:
        return np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64)
    unique_dates = np.sort(np.unique(dates))
    n_unique = unique_dates.shape[0]
    n_val_dates = int(round(val_fraction * n_unique))
    if n_val_dates <= 0:
        return np.arange(n, dtype=np.int64), np.empty(0, dtype=np.int64)
    if n_val_dates >= n_unique:
        return np.empty(0, dtype=np.int64), np.arange(n, dtype=np.int64)
    val_dates = unique_dates[-n_val_dates:]
    is_val = np.isin(dates, val_dates)
    val_idx = np.where(is_val)[0].astype(np.int64)
    train_idx = np.where(~is_val)[0].astype(np.int64)
    return train_idx, val_idx


def _length_bucketed_perm(
    L: torch.Tensor,
    batch_size: int,
    n_buckets: int = 16,
    generator: torch.Generator | None = None,
) -> torch.Tensor:
    """Length-bucketed permutation for sequence training.

    Sort by length, split into ``n_buckets`` contiguous chunks, shuffle
    within each chunk and shuffle bucket order. Reduces per-batch length
    variance so ``pack_padded_sequence`` does less work and padding
    overhead drops. SGD assumes near-iid mini-batches; with 16 buckets
    within-bucket diversity is high enough that empirical training
    dynamics are unaffected (verified against random-perm baseline).

    ``n_buckets <= 1`` recovers the prior random-shuffle behaviour and is
    bitwise-identical to ``torch.randperm`` under the same generator/seed.
    """
    n = L.shape[0]
    if n_buckets <= 1 or n <= batch_size:
        return torch.randperm(n, generator=generator)
    sorted_idx = torch.argsort(L)
    bucket_size = max(1, n // n_buckets)
    buckets = [
        sorted_idx[i * bucket_size : (i + 1) * bucket_size if i < n_buckets - 1 else n]
        for i in range(n_buckets)
    ]
    # Shuffle within bucket.
    buckets = [b[torch.randperm(len(b), generator=generator)] for b in buckets]
    # Shuffle bucket order.
    order = torch.randperm(n_buckets, generator=generator)
    return torch.cat([buckets[i] for i in order])


# ---------------------------------------------------------------------------
# Registered model class (the runner instantiates this)
# ---------------------------------------------------------------------------


@register_model("lstm")
class LSTMVolModel(_BaseModel):
    """LSTM RV forecaster — sequence-first.

    Set ``requires_sequences = True`` so the pipeline runner can dispatch a
    sequence tensor instead of a DataFrame.
    """

    REQUIRED_LAYERS: list[str] = []
    requires_sequences: bool = True
    supports_tuning: bool = True
    name = "lstm"
    family = "lstm"
    description = "LSTM sequence model with attention pooling"

    def get_arch_summary(self) -> dict[str, Any]:
        """Return architecture summary for dashboard display."""
        params = self.get_params()
        summary = {
            "hidden_dim": params.get("hidden_dim"),
            "n_layers": params.get("n_layers"),
            "bidirectional": params.get("bidirectional"),
            "dropout": params.get("dropout"),
            "loss": params.get("loss"),
            "epochs_trained": getattr(self, "epochs_run_", None),
            "best_val_loss": getattr(self, "best_val_loss_", None),
            "param_count": sum(p.numel() for p in self._module.parameters()) if self._module else None,
        }
        return summary

    def __init__(
        self,
        *,
        input_dim: int,
        hidden_dim: int = 64,
        n_layers: int = 2,
        dropout: float = 0.1,
        bidirectional: bool = False,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        max_epochs: int = 50,
        batch_size: int = 64,
        val_fraction: float = 0.15,
        early_stopping_rounds: int | None = 5,
        val_purge_gap: int = 1,
        loss: str = "qlike",
        device: str = "auto",
        precision: str = "auto",
        compile: bool = False,
        num_workers: int = 0,  # deprecated; unused (manual batching, not DataLoader)
        seed: int = 42,
        n_symbols: int = 0,
        symbol_embed_dim: int = 8,
        length_bucket_n_buckets: int = 16,
        pool_mode: str = "attention",
        head_mode: str = "mlp",
        context_dim: int = 0,
    ) -> None:
        if loss not in _LOSSES:
            raise ValueError(f"Unknown loss {loss!r}; expected one of {list(_LOSSES)}")
        if val_fraction < 0 or val_fraction >= 1:
            raise ValueError(f"val_fraction must be in [0, 1), got {val_fraction}")

        self.input_dim = int(input_dim)
        self.hidden_dim = int(hidden_dim)
        self.n_layers = int(n_layers)
        self.dropout = float(dropout)
        self.bidirectional = bool(bidirectional)
        self.learning_rate = float(learning_rate)
        self.weight_decay = float(weight_decay)
        self.max_epochs = int(max_epochs)
        self.batch_size = int(batch_size)
        self.val_fraction = float(val_fraction)
        self.early_stopping_rounds = int(early_stopping_rounds) if early_stopping_rounds else 0
        self.val_purge_gap = int(val_purge_gap)
        self.loss = loss
        self.device = _resolve_device(device)
        self.precision = precision
        self.compile = bool(compile)
        self.num_workers = int(num_workers)  # unused; kept for config/save-load compat
        if self.num_workers != 0:
            import warnings
            warnings.warn(
                "LSTMVolModel.num_workers is unused (manual batching, not "
                "DataLoader). Set to 0 or remove from config. This argument "
                "will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
        self.seed = int(seed)
        self.n_symbols = int(n_symbols)
        self.symbol_embed_dim = int(symbol_embed_dim)
        # Step 1.3: per-epoch length-bucketed shuffle. ``1`` recovers the
        # prior random-shuffle behaviour (bitwise-identical under same seed).
        self.length_bucket_n_buckets = int(length_bucket_n_buckets)
        self.pool_mode = str(pool_mode)
        self.head_mode = str(head_mode)
        self.context_dim = int(context_dim)

        self._context_mean: np.ndarray | None = None
        self._context_std: np.ndarray | None = None

        self._module: nn.Module | None = None
        self._compiled: nn.Module | None = None
        self.epochs_run_: int = 0
        self.best_val_loss_: float | None = None
        self.history_: list[dict[str, float]] = []
        # Residual-learning flag: when fit with ``base_preds``, predict
        # must also receive ``base_preds`` and adds them back to the LSTM
        # output. See trial-052 design (stacked HAR-IV / LightGBM + LSTM).
        self.was_fit_with_base_preds: bool = False
        # Symbol identity mapping (set by runner before fit for pooled training).
        self.symbol_to_id: dict[str, int] | None = None

    # ---- HPO (Optuna) ----------------------------------------------------

    @classmethod
    def tune_and_fit(
        cls,
        seq: SequenceTensor,
        y: pd.Series | np.ndarray,
        *,
        tuning_config,
        base_preds: np.ndarray | torch.Tensor | pd.Series | None = None,
        symbol_ids: np.ndarray | torch.Tensor | None = None,
        base_params: dict[str, Any] | None = None,
        idx: pd.MultiIndex | None = None,
        base_cfg_dict: dict | None = None,
        base_X: pd.DataFrame | None = None,
        base_y: pd.Series | None = None,
        norm_mode: str = "pooled",
        n_gpus: int = 1,
        progress_queue: Any | None = None,
        on_progress: Any | None = None,
    ) -> LSTMVolModel:
        """Tune hyperparameters via Optuna, then fit on full data with best params.

        Parameters
        ----------
        seq : SequenceTensor
            Full training sequences.
        y : array-like
            Target values.
        tuning_config : TuningConfig
            Tuning configuration (n_trials, timeout, inner_cv, etc.).
        base_preds : array-like, optional
            Base model predictions for residual learning.
        symbol_ids : array-like, optional
            Symbol identifiers.
        base_params : dict, optional
            Fixed params from config (merged into every trial, not searched).
        idx : pd.MultiIndex, optional
            Panel index for CV splitting. If None, uses seq.dates.
        base_cfg_dict : dict, optional
            Base model config dict for inner fold re-training.
        base_X : pd.DataFrame, optional
            Base model features for inner fold fitting.
        base_y : pd.Series, optional
            Base model targets for inner fold fitting.
        norm_mode : str
            Normalisation mode.
        n_gpus : int
            Number of GPUs for parallel trials.
        progress_queue : mp.Queue, optional
            Progress queue for UI updates.
        on_progress : callable, optional
            Progress callback for final refit.

        Returns
        -------
        LSTMVolModel
            Fitted model with Optuna-tuned hyperparameters.
        """
        from volforecast.models.lstm_tuning import tune_lstm_hyperparameters

        if base_params is None:
            base_params = {}

        # Separate fixed params (not searched) from the search space
        _TUNABLE_KEYS = {"hidden_dim", "n_layers", "learning_rate", "dropout", "weight_decay", "batch_size"}
        fixed_params = {k: v for k, v in base_params.items() if k not in _TUNABLE_KEYS}
        # Ensure essential fixed params are present
        fixed_params.setdefault("bidirectional", True)
        fixed_params.setdefault("max_epochs", 80)
        fixed_params.setdefault("early_stopping_rounds", 7)
        fixed_params.setdefault("val_fraction", 0.15)
        fixed_params.setdefault("loss", "qlike")
        fixed_params.setdefault("precision", "auto")
        fixed_params.setdefault("compile", True)

        # Prepare tensor data
        tensor = seq.tensor
        lengths_t = seq.lengths

        # Share memory for cross-process access
        if not tensor.is_shared():
            tensor.share_memory_()
        if not lengths_t.is_shared():
            lengths_t.share_memory_()

        # Prepare y as numpy
        if isinstance(y, pd.Series):
            y_values = y.values.astype(np.float64)
        else:
            y_values = np.asarray(y, dtype=np.float64)

        # Prepare symbol_ids as numpy
        if symbol_ids is not None:
            if isinstance(symbol_ids, torch.Tensor):
                sym_ids_np = symbol_ids.numpy().astype(np.int64)
            else:
                sym_ids_np = np.asarray(symbol_ids, dtype=np.int64)
        else:
            sym_ids_np = np.zeros(len(seq), dtype=np.int64)

        # Build panel index if not provided
        if idx is None:
            idx = pd.MultiIndex.from_arrays(
                [seq.dates, ["_"] * len(seq.dates)], names=["date", "symbol"]
            )

        # Inner CV config
        inner_cv = tuning_config.inner_cv
        if inner_cv is None:
            from volforecast.config import CVConfig
            inner_cv = CVConfig(
                method="expanding_window",
                purge_gap=10,
                train_size=756,
                test_size=126,
            )

        # Storage dir
        storage_dir = tuning_config.storage_dir

        # Run HPO
        best_params = tune_lstm_hyperparameters(
            tensor=tensor,
            lengths=lengths_t,
            y_values=y_values,
            symbol_ids=sym_ids_np,
            idx=idx,
            spec_features=tuple(seq.feature_names),
            cv_config=inner_cv,
            n_trials=tuning_config.n_trials,
            n_gpus=n_gpus,
            timeout=tuning_config.timeout,
            seed=fixed_params.get("seed", 42),
            base_cfg_dict=base_cfg_dict,
            base_X=base_X,
            base_y=base_y,
            norm_mode=norm_mode,
            fixed_params=fixed_params,
            storage_dir=storage_dir,
            progress_queue=progress_queue,
        )

        # Merge best params with fixed params for final refit
        final_params = {**fixed_params, **best_params}
        final_params["input_dim"] = int(tensor.shape[2])
        final_params["device"] = "auto"  # Let it pick best device for refit

        # Set n_symbols if symbol embeddings are active
        if fixed_params.get("n_symbols", 0) > 0:
            final_params["n_symbols"] = fixed_params["n_symbols"]
            final_params["symbol_embed_dim"] = fixed_params.get("symbol_embed_dim", 8)

        logger.info("LSTM HPO refit with best params: %s", final_params)

        # Final refit on full training data
        model = cls(**final_params)
        fit_kwargs: dict[str, Any] = {}
        if symbol_ids is not None and model.n_symbols > 0:
            fit_kwargs["symbol_ids"] = symbol_ids
        if base_preds is not None:
            fit_kwargs["base_preds"] = base_preds
        if on_progress is not None:
            fit_kwargs["on_progress"] = on_progress

        model.fit(seq, y, **fit_kwargs)
        return model

    # ---- helpers ---------------------------------------------------------

    def _set_seed(self) -> None:
        torch.manual_seed(self.seed)
        if self.device == "cuda":
            torch.cuda.manual_seed_all(self.seed)

    def _build_module(self) -> nn.Module:
        return _LSTMBody(
            input_dim=self.input_dim,
            hidden_dim=self.hidden_dim,
            n_layers=self.n_layers,
            dropout=self.dropout,
            bidirectional=self.bidirectional,
            n_symbols=self.n_symbols,
            symbol_embed_dim=self.symbol_embed_dim,
            pool_mode=self.pool_mode,
            head_mode=self.head_mode,
            context_dim=self.context_dim,
        ).to(self.device)

    def _maybe_compile(self, body: nn.Module) -> nn.Module:
        if not self.compile or self.device == "cpu":
            return body
        try:
            # Suppress noisy cudagraph partition warnings from torch.compile
            # (expected due to CPU length-sort in pack_padded_sequence path).
            logging.getLogger("torch._inductor.utils").setLevel(logging.ERROR)

            # Packed sequences always produce variable-length tensors per batch.
            # dynamic=True is required for both paths to avoid CUDA Graph
            # recompilation storms. With symbol embedding, use mode="default"
            # (symbol_ids add another varying input). Without embedding,
            # reduce-overhead + dynamic handles the packed-sequence variability.
            # We raise the recompile limit because pack_padded_sequence with
            # varying batch sizes can trigger legitimate re-specializations
            # beyond the default limit of 8.
            import torch._dynamo

            torch._dynamo.config.recompile_limit = 16
            if self.n_symbols > 0:
                return torch.compile(body, mode="default", dynamic=True)
            return torch.compile(body, mode="reduce-overhead", dynamic=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("torch.compile failed (%s); running uncompiled", exc)
            return body

    def _align_targets(
        self, seq: SequenceTensor, y: pd.Series | np.ndarray
    ) -> tuple[torch.Tensor, np.ndarray]:
        """Return (target tensor, retained-dates mask).

        The pipeline may give us a Series indexed by date or a bare array
        already aligned to ``seq.dates``. Drops any date whose target is NaN.
        """
        if isinstance(y, pd.Series):
            aligned = y.reindex(seq.dates)
        else:
            arr = np.asarray(y, dtype=np.float32)
            if arr.shape[0] != len(seq):
                raise ValueError(f"Target length {arr.shape[0]} != seq length {len(seq)}")
            aligned = pd.Series(arr, index=seq.dates)
        finite_mask = aligned.notna().values
        y_kept = aligned.values[finite_mask].astype(np.float32)
        return torch.from_numpy(y_kept), finite_mask

    @staticmethod
    def _validate_base_preds(
        base_preds: np.ndarray | torch.Tensor | pd.Series | None,
        n_expected: int,
        *,
        context: str,
    ) -> np.ndarray | None:
        """Coerce ``base_preds`` to a float32 numpy array of length ``n_expected``.

        Returns ``None`` when ``base_preds`` is ``None`` (caller handles the
        no-base path). Raises ``ValueError`` on length mismatch — the runner
        is expected to slice base_preds to match the sequence subset BEFORE
        calling fit/predict.
        """
        if base_preds is None:
            return None
        if isinstance(base_preds, pd.Series):
            arr = base_preds.values
        elif isinstance(base_preds, torch.Tensor):
            arr = base_preds.detach().cpu().numpy()
        else:
            arr = np.asarray(base_preds)
        arr = arr.astype(np.float32, copy=False)
        if arr.shape[0] != n_expected:
            raise ValueError(
                f"base_preds length {arr.shape[0]} != expected {n_expected} ({context})"
            )
        return arr

    # ---- training --------------------------------------------------------

    def fit(
        self,
        seq: SequenceTensor,
        y: pd.Series | np.ndarray,
        *,
        base_preds: np.ndarray | torch.Tensor | pd.Series | None = None,
        symbol_ids: np.ndarray | torch.Tensor | None = None,
        context: np.ndarray | None = None,
        on_progress: Any | None = None,
        on_batch_progress: Any | None = None,
    ) -> LSTMVolModel:
        """Train on ``seq`` with target ``y`` (one log-RV per date).

        Parameters
        ----------
        seq : SequenceTensor
            Per-day padded tensor + valid lengths.
        y : pd.Series | np.ndarray
            Log-RV target, one per date in ``seq.dates``.
        base_preds : array-like, optional
            Tabular base-model predictions (log-RV space), one per date in
            ``seq.dates``. When provided, the LSTM trains on the residual
            ``y - base_preds`` and ``predict`` MUST also receive
            ``base_preds`` (the LSTM output is added back to the base). The
            runner is responsible for fitting the base model on each fold's
            training set and threading the predictions through here.
        symbol_ids : array-like, optional
            Integer symbol identifiers, one per date in ``seq.dates``.
            Required when ``n_symbols > 0``. Used to index the learned
            symbol embedding that gives the LSTM identity awareness.
        on_progress : callable, optional
            Called as ``on_progress(current_epoch, max_epochs)`` at the end
            of every training epoch. Signature mirrors the LightGBM
            ``on_progress`` callback so the CLI can render a uniform nested
            progress bar across model classes.
        on_batch_progress : callable, optional
            Called as ``on_batch_progress(current_batch, total_batches,
            current_epoch, total_epochs)`` during training. Throttled to
            roughly 20 updates per epoch (always fired on the first batch
            and on the final batch of each epoch). Lets the CLI render an
            intra-epoch loading bar for very long epochs.
        """
        if seq.n_features != self.input_dim:
            raise ValueError(f"input_dim={self.input_dim} but seq has {seq.n_features} features")
        self._set_seed()

        if self.device.startswith("cuda"):
            torch.set_float32_matmul_precision("high")
            torch.backends.cudnn.benchmark = True

        base_arr = self._validate_base_preds(
            base_preds, n_expected=len(seq), context="fit: must match len(seq.dates)"
        )
        self.was_fit_with_base_preds = base_arr is not None

        y_tensor, finite_mask = self._align_targets(seq, y)
        if base_arr is not None:
            # Slice base with the same finite-mask used on y, then subtract
            # to form the residual the LSTM actually trains on.
            base_kept = base_arr[finite_mask]
            y_tensor = y_tensor - torch.from_numpy(base_kept)
        kept_idx = torch.from_numpy(np.where(finite_mask)[0]).to(torch.long)
        X = seq.tensor.index_select(0, kept_idx)
        L = seq.lengths.index_select(0, kept_idx)

        # Thread symbol_ids through the finite-mask.
        sym_ids_t: torch.Tensor | None = None
        if symbol_ids is not None:
            if isinstance(symbol_ids, np.ndarray):
                sym_ids_t = torch.from_numpy(symbol_ids).to(torch.long)
            else:
                sym_ids_t = symbol_ids.to(torch.long)
            sym_ids_t = sym_ids_t[kept_idx]

        # Thread context through the finite-mask.
        if context is not None and self.context_dim == 0:
            raise ValueError(
                "fit: context array provided but model has context_dim=0"
            )
        if context is None and self.context_dim > 0:
            raise ValueError(
                "fit: model has context_dim>0 but no context array provided"
            )
        context_kept: np.ndarray | None = None
        if context is not None:
            context = np.asarray(context, dtype=np.float32)
            if context.shape[0] != len(seq):
                raise ValueError(
                    f"fit: context length {context.shape[0]} != len(seq) {len(seq)}"
                )
            context_kept = context[finite_mask]

        # Step 1.2: split unique DATES (not rows) — pooled training has
        # multiple symbols per date, so a row-count split could leak
        # symbols of the same date across the train/val boundary used by
        # early stopping. See _split_train_val_by_date for the pure helper.
        dates_kept = seq.dates.values[finite_mask]
        train_pos, val_pos = _split_train_val_by_date(dates_kept, self.val_fraction)
        # Optional date-level purge between train tail and val: drop the
        # last ``val_purge_gap`` unique train dates so they cannot leak
        # forward-RV labels into the early-stopping validation set at h>1.
        # Pre-existing behaviour operated on rows; we now operate on dates
        # to match the date-aware split.
        if (
            self.val_purge_gap > 0
            and len(train_pos) > 0
            and len(val_pos) > 0
        ):
            train_dates_arr = dates_kept[train_pos]
            unique_train_dates = np.sort(np.unique(train_dates_arr))
            purge_n = min(int(self.val_purge_gap), len(unique_train_dates) // 2)
            if purge_n > 0:
                purge_dates = set(unique_train_dates[-purge_n:].tolist())
                keep_mask = np.array(
                    [d not in purge_dates for d in train_dates_arr], dtype=bool
                )
                train_pos = train_pos[keep_mask]
        # Expose the date partition for tests (lightweight, only sets/tuple).
        train_dates_set = set(dates_kept[train_pos].tolist())
        val_dates_set = set(dates_kept[val_pos].tolist())
        self._last_split_dates: tuple[set, set] = (train_dates_set, val_dates_set)

        # Context normalisation: compute stats from training portion only.
        ctx_t: torch.Tensor | None = None
        if context_kept is not None:
            self._context_mean = context_kept[train_pos].mean(axis=0)
            self._context_std = context_kept[train_pos].std(axis=0)
            self._context_std = np.maximum(self._context_std, 1e-8)
            context_normed = (context_kept - self._context_mean) / self._context_std
            context_normed = np.nan_to_num(context_normed, nan=0.0).astype(np.float32)
            ctx_t = torch.from_numpy(context_normed)

        if (
            len(val_pos) > 0
            and len(train_pos) > 0
            and self.early_stopping_rounds > 0
        ):
            train_idx_t = torch.from_numpy(train_pos)
            val_idx_t = torch.from_numpy(val_pos)
            X_tr = X.index_select(0, train_idx_t)
            X_va = X.index_select(0, val_idx_t)
            L_tr = L.index_select(0, train_idx_t)
            L_va = L.index_select(0, val_idx_t)
            y_tr = y_tensor.index_select(0, train_idx_t)
            y_va = y_tensor.index_select(0, val_idx_t)
            sym_tr = sym_ids_t.index_select(0, train_idx_t) if sym_ids_t is not None else None
            sym_va = sym_ids_t.index_select(0, val_idx_t) if sym_ids_t is not None else None
            ctx_tr = ctx_t.index_select(0, train_idx_t) if ctx_t is not None else None
            ctx_va = ctx_t.index_select(0, val_idx_t) if ctx_t is not None else None
            use_val = True
        else:
            X_tr, L_tr, y_tr = X, L, y_tensor
            X_va = L_va = y_va = None
            sym_tr = sym_ids_t
            sym_va = None
            ctx_tr = ctx_t
            ctx_va = None
            use_val = False

        # A2: replace DataLoader/TensorDataset with manual index permutation.
        # Our tensors are already in RAM (no disk I/O), so DataLoader's
        # multiprocessing + collation adds pure overhead. Manual slicing
        # preserves the same shuffle semantics as ``DataLoader(shuffle=True)``
        # because both internally call ``torch.randperm(n)`` once per epoch
        # from ``torch.default_generator`` — see test_lstm_optim.py.
        n_train = X_tr.shape[0]

        # A9: Move training data to device once at the start. Per-batch
        # .to(device) is replaced by on-device indexing (free). L_tr stays
        # on CPU (pack_padded_sequence requirement). Memory footprint is
        # ~2GB/fold on an 80GB H100 — trivial.
        if self.device != "cpu":
            X_tr = X_tr.to(self.device)
            y_tr = y_tr.to(self.device)
            if sym_tr is not None:
                sym_tr = sym_tr.to(self.device)
            if ctx_tr is not None:
                ctx_tr = ctx_tr.to(self.device)
            if use_val:
                X_va = X_va.to(self.device)
                y_va = y_va.to(self.device)
                if sym_va is not None:
                    sym_va = sym_va.to(self.device)
                if ctx_va is not None:
                    ctx_va = ctx_va.to(self.device)

        body = self._build_module()
        self._module = body
        self._compiled = self._maybe_compile(body)
        # Note: tried fused AdamW (A1) — measured 0.96× on H100 medium bench
        # (workspace/tmp/lstm-bench-A1_fused_adamw.json). Reverted: the LSTM
        # has too few param tensors (13) for the fused launch to amortise.
        opt = torch.optim.AdamW(
            body.parameters(),
            lr=self.learning_rate,
            weight_decay=self.weight_decay,
        )
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            opt, mode="min", factor=0.5, patience=2
        )
        criterion = _LOSSES[self.loss]
        autocast_dtype = _resolve_precision(self.precision, self.device)

        # Visible device banner (stdout, not just logger) so users always
        # know whether training is running on the GPU. Only print once per
        # model instance to avoid log spam across many CV folds.
        device_label = self.device
        if self.device == "cuda":
            try:
                device_label = f"cuda:{torch.cuda.current_device()} ({torch.cuda.get_device_name(0)})"
            except Exception:  # noqa: BLE001
                device_label = "cuda (name unavailable)"
        precision_label = (
            "bf16"
            if autocast_dtype == torch.bfloat16
            else "fp16"
            if autocast_dtype == torch.float16
            else "fp32"
        )
        if not getattr(LSTMVolModel, "_banner_printed", False):
            print(
                f"[lstm] training on device={device_label} precision={precision_label} "
                f"compile={self.compile and self.device != 'cpu'} "
                f"params={sum(p.numel() for p in body.parameters())} "
                f"train={X_tr.shape[0]} val={X_va.shape[0] if use_val else 0} "
                f"batches/epoch={math.ceil(X_tr.shape[0] / self.batch_size)} loss={self.loss}",
                flush=True,
            )
            LSTMVolModel._banner_printed = True

        logger.info(
            "LSTM fit: device=%s precision=%s compile=%s params=%d "
            "train=%d val=%d batches/epoch=%d loss=%s",
            device_label,
            precision_label,
            self.compile and self.device != "cpu",
            sum(p.numel() for p in body.parameters()),
            X_tr.shape[0],
            X_va.shape[0] if use_val else 0,
            math.ceil(X_tr.shape[0] / self.batch_size),
            self.loss,
        )

        best_val = math.inf
        bad_epochs = 0
        best_state: dict[str, torch.Tensor] | None = None

        self.epochs_run_ = 0
        self.history_ = []
        total_batches_per_epoch = math.ceil(n_train / self.batch_size)
        # Throttle batch callbacks to ~20 updates per epoch so very long
        # epochs still produce frequent feedback but tiny epochs don't spam
        # the UI. We always fire on batch 1 and on the final batch.
        batch_update_stride = max(1, total_batches_per_epoch // 20)
        # OOM recovery: track effective batch size (may shrink on OOM).
        effective_batch_size = self.batch_size
        _oom_retries = 0
        _MAX_OOM_RETRIES = 3
        for epoch in range(1, self.max_epochs + 1):
            body.train()
            # A5: accumulate loss on-device as a 0-d tensor and sync once per
            # epoch instead of calling .item() per batch (each .item() forces
            # a device-host sync that blocks the CUDA stream).
            train_loss_sum = torch.zeros((), device=self.device)
            n_batches = 0
            # A2: manual shuffle via randperm — uses ``torch.default_generator``
            # which we seed in ``_set_seed`` so the shuffle is reproducible for
            # a given (seed, epoch) pair. This produces a different shuffle
            # sequence than the old ``DataLoader(shuffle=True)`` path (because
            # DataLoader's RandomSampler re-seeds an internal generator each
            # epoch), but the training procedure is mathematically identical:
            # uniform mini-batch SGD over the same data with the same
            # optimiser. Verified equivalent end-of-fit loss across seeds.
            # Step 1.3: length-bucketed shuffle reduces per-batch L variance
            # so pack_padded_sequence does less work. n_buckets=1 falls back
            # to pure torch.randperm (legacy behaviour).
            perm = _length_bucketed_perm(
                L_tr, effective_batch_size, n_buckets=self.length_bucket_n_buckets
            )
            for start in range(0, n_train, effective_batch_size):
                batch_idx = perm[start : start + effective_batch_size]
                xb = X_tr[batch_idx]
                # A4: keep lb on CPU — pack_padded_sequence requires CPU lengths.
                lb = L_tr[batch_idx]
                yb = y_tr[batch_idx]
                sym_b = sym_tr[batch_idx] if sym_tr is not None else None
                ctx_b = ctx_tr[batch_idx] if ctx_tr is not None else None
                opt.zero_grad(set_to_none=True)
                try:
                    if autocast_dtype is not None:
                        with torch.autocast(device_type=self.device, dtype=autocast_dtype):
                            pred = self._compiled(xb, lb, sym_b, ctx_b)
                            loss = criterion(pred.float(), yb)
                    else:
                        pred = self._compiled(xb, lb, sym_b, ctx_b)
                        loss = criterion(pred, yb)
                    loss.backward()
                except torch.cuda.OutOfMemoryError:
                    _oom_retries += 1
                    if _oom_retries > _MAX_OOM_RETRIES:
                        raise
                    # Free fragmented memory and halve the batch size.
                    torch.cuda.empty_cache()
                    effective_batch_size = max(1, effective_batch_size // 2)
                    total_batches_per_epoch = math.ceil(n_train / effective_batch_size)
                    batch_update_stride = max(1, total_batches_per_epoch // 20)
                    logger.warning(
                        "CUDA OOM at epoch %d — reducing batch_size to %d (retry %d/%d)",
                        epoch, effective_batch_size, _oom_retries, _MAX_OOM_RETRIES,
                    )
                    break  # restart this epoch with smaller batches
                torch.nn.utils.clip_grad_norm_(body.parameters(), max_norm=5.0)
                opt.step()
                train_loss_sum = train_loss_sum + loss.detach()
                n_batches += 1
                # Throttled intra-epoch progress callback.
                if on_batch_progress is not None and (
                    n_batches == 1
                    or n_batches == total_batches_per_epoch
                    or n_batches % batch_update_stride == 0
                ):
                    on_batch_progress(
                        n_batches, total_batches_per_epoch, epoch, self.max_epochs
                    )
            else:
                # for/else: this block runs only when the batch loop completed
                # without break (i.e., no OOM). Proceed to epoch bookkeeping.
                pass

            if n_batches == 0:
                # OOM broke the batch loop before any step completed — retry.
                continue

            tr_loss = float(train_loss_sum.item() / n_batches) if n_batches else float("nan")
            entry: dict[str, float] = {"epoch": epoch, "train_loss": tr_loss}

            if use_val:
                val_loss = self._eval_loss(X_va, L_va, y_va, criterion, autocast_dtype, symbol_ids=sym_va, context=ctx_va)
                entry["val_loss"] = val_loss
                scheduler.step(val_loss)
                improved = val_loss + 1e-6 < best_val
                if improved:
                    best_val = val_loss
                    bad_epochs = 0
                    best_state = {k: v.detach().cpu().clone() for k, v in body.state_dict().items()}
                else:
                    bad_epochs += 1
                self.epochs_run_ = epoch
                self.history_.append(entry)
                if on_progress is not None:
                    on_progress(epoch, self.max_epochs)
                if self.early_stopping_rounds and bad_epochs >= self.early_stopping_rounds:
                    logger.info(
                        "Early stopping at epoch %d (best val=%.5f, patience=%d)",
                        epoch,
                        best_val,
                        self.early_stopping_rounds,
                    )
                    break
            else:
                self.epochs_run_ = epoch
                self.history_.append(entry)
                if on_progress is not None:
                    on_progress(epoch, self.max_epochs)

        if use_val and best_state is not None:
            body.load_state_dict(best_state)
            self.best_val_loss_ = best_val

        return self

    def _eval_loss(
        self,
        X: torch.Tensor,
        L: torch.Tensor,
        y: torch.Tensor,
        criterion,
        autocast_dtype: torch.dtype | None,
        symbol_ids: torch.Tensor | None = None,
        context: torch.Tensor | None = None,
    ) -> float:
        body = self._module
        assert body is not None
        body.eval()
        # A5: accumulate on-device, single sync at the end.
        loss_sum = torch.zeros((), device=self.device)
        n_batches = 0
        with torch.no_grad():
            for start in range(0, X.shape[0], self.batch_size):
                xb = X[start : start + self.batch_size]
                lb = L[start : start + self.batch_size]  # A4: stays on CPU
                yb = y[start : start + self.batch_size]
                sym_b = symbol_ids[start : start + self.batch_size] if symbol_ids is not None else None
                ctx_b = context[start : start + self.batch_size] if context is not None else None
                if autocast_dtype is not None:
                    with torch.autocast(device_type=self.device, dtype=autocast_dtype):
                        pred = self._compiled(xb, lb, sym_b, ctx_b)
                        loss = criterion(pred.float(), yb)
                else:
                    pred = self._compiled(xb, lb, sym_b, ctx_b)
                    loss = criterion(pred, yb)
                loss_sum = loss_sum + loss.detach()
                n_batches += 1
        return float(loss_sum.item() / n_batches) if n_batches else float("nan")

    # ---- inference -------------------------------------------------------

    def predict(
        self,
        seq: SequenceTensor,
        *,
        base_preds: np.ndarray | torch.Tensor | pd.Series | None = None,
        symbol_ids: np.ndarray | torch.Tensor | None = None,
        context: np.ndarray | None = None,
    ) -> np.ndarray:
        """Predict log-RV for each row of ``seq``.

        When the model was fit with ``base_preds``, the caller MUST supply
        ``base_preds`` here (length == ``len(seq.dates)``); the LSTM output
        is added back to the base. When the model was fit without
        ``base_preds``, supplying them here raises — silent prediction
        drift would be worse than a fail-loud error.
        """
        if self._module is None:
            raise RuntimeError("LSTMVolModel.predict called before fit")
        if self.was_fit_with_base_preds and base_preds is None:
            raise ValueError(
                "predict: this model was fit with base_preds; you MUST pass "
                "base_preds to predict (length == len(seq.dates))."
            )
        if not self.was_fit_with_base_preds and base_preds is not None:
            raise ValueError(
                "predict: this model was fit WITHOUT base_preds; passing "
                "base_preds at predict time would silently shift outputs."
            )
        # Validate context
        if context is not None and self.context_dim == 0:
            raise ValueError(
                "predict: context array provided but model has context_dim=0"
            )
        if context is None and self.context_dim > 0:
            raise ValueError(
                "predict: model has context_dim>0 but no context array provided"
            )
        base_arr = self._validate_base_preds(
            base_preds, n_expected=len(seq), context="predict: must match len(seq.dates)"
        )
        # Prepare context tensor
        ctx_t: torch.Tensor | None = None
        if context is not None:
            context = np.asarray(context, dtype=np.float32)
            if context.shape[0] != len(seq):
                raise ValueError(
                    f"predict: context length {context.shape[0]} != len(seq) {len(seq)}"
                )
            context_normed = (context - self._context_mean) / self._context_std
            context_normed = np.nan_to_num(context_normed, nan=0.0).astype(np.float32)
            ctx_t = torch.from_numpy(context_normed).to(self.device)
        # Prepare symbol_ids tensor
        sym_ids_t: torch.Tensor | None = None
        if symbol_ids is not None:
            if isinstance(symbol_ids, np.ndarray):
                sym_ids_t = torch.from_numpy(symbol_ids).to(dtype=torch.long, device=self.device)
            else:
                sym_ids_t = symbol_ids.to(dtype=torch.long, device=self.device)
        # Use the compiled wrapper when available (it falls back to the raw
        # module on CPU or when ``compile=False``). Always call ``eval()``
        # on the underlying ``_module`` — ``torch.compile`` proxies that
        # through, but a plain wrapper may not.
        body = self._compiled if self._compiled is not None else self._module
        self._module.eval()
        autocast_dtype = _resolve_precision(self.precision, self.device)
        out_chunks: list[torch.Tensor] = []
        with torch.no_grad():
            for start in range(0, len(seq), self.batch_size):
                xb = seq.tensor[start : start + self.batch_size].to(self.device, non_blocking=True)
                lb = seq.lengths[start : start + self.batch_size]  # A4: CPU
                sym_b = sym_ids_t[start : start + self.batch_size] if sym_ids_t is not None else None
                ctx_b = ctx_t[start : start + self.batch_size] if ctx_t is not None else None
                if autocast_dtype is not None:
                    with torch.autocast(device_type=self.device, dtype=autocast_dtype):
                        pred = body(xb, lb, sym_b, ctx_b).float()
                else:
                    pred = body(xb, lb, sym_b, ctx_b)
                out_chunks.append(pred.detach().cpu())
        out = torch.cat(out_chunks, dim=0).numpy().astype(np.float32)
        if base_arr is not None:
            out = out + base_arr
        return out

    # ---- feature extraction (for feature stacking) -----------------------

    def extract_features(
        self,
        seq: SequenceTensor,
        *,
        outputs: list[str] | None = None,
        base_preds: np.ndarray | torch.Tensor | pd.Series | None = None,
        symbol_ids: np.ndarray | torch.Tensor | None = None,
    ) -> dict[str, np.ndarray]:
        """Extract configurable features from a fitted LSTM for stacking.

        Parameters
        ----------
        seq : SequenceTensor
            Sequence data (same format as predict).
        outputs : list[str]
            Which features to extract. Valid values:
            - "prediction": scalar log-RV prediction (B,)
            - "attention_entropy": Shannon entropy of attention weights (B,)
            - "attention_peak_time": normalized argmax of attention (B,)
            - "embedding": pooled hidden state before MLP head (B, H)
        base_preds : array-like, optional
            Required if model was fit with base_preds (added to prediction).
        symbol_ids : array-like, optional
            Symbol identifiers for pooled models.

        Returns
        -------
        dict[str, np.ndarray]
            Keys are the requested output names, values are numpy arrays.
        """
        if self._module is None:
            raise RuntimeError("extract_features called before fit")
        if outputs is None:
            outputs = ["prediction"]

        valid_outputs = {"prediction", "attention_entropy", "attention_peak_time", "embedding"}
        invalid = set(outputs) - valid_outputs
        if invalid:
            raise ValueError(f"Invalid outputs: {invalid}. Valid: {valid_outputs}")

        base_arr = self._validate_base_preds(
            base_preds, n_expected=len(seq), context="extract_features"
        )

        sym_ids_t: torch.Tensor | None = None
        if symbol_ids is not None:
            if isinstance(symbol_ids, np.ndarray):
                sym_ids_t = torch.from_numpy(symbol_ids).to(dtype=torch.long, device=self.device)
            else:
                sym_ids_t = symbol_ids.to(dtype=torch.long, device=self.device)

        body: _LSTMBody = self._module  # type: ignore[assignment]
        body.eval()
        # ``torch.compile`` preserves ``forward_with_internals`` on the
        # OptimizedModule wrapper (verified at workspace/tmp/), so we can
        # route through ``self._compiled`` when present for the same speedup
        # the training loop gets. ``self._module.eval()`` above already
        # toggled eval mode on the underlying module.
        body_for_forward = self._compiled if self._compiled is not None else body
        autocast_dtype = _resolve_precision(self.precision, self.device)

        pred_chunks: list[torch.Tensor] = []
        embed_chunks: list[torch.Tensor] = []
        entropy_chunks: list[torch.Tensor] = []
        peak_chunks: list[torch.Tensor] = []

        with torch.no_grad():
            for start in range(0, len(seq), self.batch_size):
                xb = seq.tensor[start : start + self.batch_size].to(self.device, non_blocking=True)
                lb = seq.lengths[start : start + self.batch_size]
                sym_b = sym_ids_t[start : start + self.batch_size] if sym_ids_t is not None else None

                if autocast_dtype is not None:
                    with torch.autocast(device_type=self.device, dtype=autocast_dtype):
                        prediction, pooled, weights = body_for_forward.forward_with_internals(xb, lb, sym_b)
                        prediction = prediction.float()
                        pooled = pooled.float()
                        weights = weights.float()
                else:
                    prediction, pooled, weights = body_for_forward.forward_with_internals(xb, lb, sym_b)

                # Build mask for attention utilities
                arange = torch.arange(xb.shape[1], device=xb.device).unsqueeze(0)
                mask = arange < lb.to(xb.device).unsqueeze(1)

                pred_chunks.append(prediction.detach().cpu())
                if "embedding" in outputs:
                    embed_chunks.append(pooled.detach().cpu())
                if "attention_entropy" in outputs:
                    entropy_chunks.append(
                        compute_attention_entropy(weights, mask).detach().cpu()
                    )
                if "attention_peak_time" in outputs:
                    peak_chunks.append(
                        compute_attention_peak_time(weights, seq.tensor.shape[1]).detach().cpu()
                    )

        result: dict[str, np.ndarray] = {}

        if "prediction" in outputs:
            preds = torch.cat(pred_chunks, dim=0).numpy().astype(np.float32)
            if base_arr is not None:
                preds = preds + base_arr
            result["prediction"] = preds

        if "attention_entropy" in outputs:
            result["attention_entropy"] = torch.cat(entropy_chunks, dim=0).numpy().astype(np.float32)

        if "attention_peak_time" in outputs:
            result["attention_peak_time"] = torch.cat(peak_chunks, dim=0).numpy().astype(np.float32)

        if "embedding" in outputs:
            result["embedding"] = torch.cat(embed_chunks, dim=0).numpy().astype(np.float32)

        return result

    # ---- persistence -----------------------------------------------------

    def save(self, path: Path) -> Path:
        if self._module is None:
            raise RuntimeError("LSTMVolModel.save called before fit")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 3,
            "init_kwargs": self.get_params(),
            "state_dict": {k: v.detach().cpu() for k, v in self._module.state_dict().items()},
            "epochs_run": self.epochs_run_,
            "best_val_loss": self.best_val_loss_,
            "was_fit_with_base_preds": self.was_fit_with_base_preds,
            "symbol_to_id": self.symbol_to_id,
        }
        tmp = path.with_suffix(path.suffix + ".tmp")
        torch.save(payload, tmp)
        os.replace(tmp, path)
        return path

    @classmethod
    def load(cls, path: Path) -> LSTMVolModel:
        payload = torch.load(Path(path), map_location="cpu", weights_only=False)
        instance = cls(**payload["init_kwargs"])
        instance._module = instance._build_module()
        instance._compiled = instance._maybe_compile(instance._module)
        instance._module.load_state_dict(payload["state_dict"])
        instance.epochs_run_ = payload.get("epochs_run", 0)
        instance.best_val_loss_ = payload.get("best_val_loss")
        # Backward compat: older payloads (schema_version=1) lack this flag.
        instance.was_fit_with_base_preds = bool(payload.get("was_fit_with_base_preds", False))
        # Schema v3: symbol identity mapping.
        instance.symbol_to_id = payload.get("symbol_to_id")
        return instance

    # ---- tournament tooling ---------------------------------------------

    def get_params(self) -> dict[str, Any]:
        return {
            "input_dim": self.input_dim,
            "hidden_dim": self.hidden_dim,
            "n_layers": self.n_layers,
            "dropout": self.dropout,
            "bidirectional": self.bidirectional,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "max_epochs": self.max_epochs,
            "batch_size": self.batch_size,
            "val_fraction": self.val_fraction,
            "early_stopping_rounds": self.early_stopping_rounds,
            "val_purge_gap": self.val_purge_gap,
            "loss": self.loss,
            "device": self.device,
            "precision": self.precision,
            "compile": self.compile,
            "num_workers": self.num_workers,
            "seed": self.seed,
            "n_symbols": self.n_symbols,
            "symbol_embed_dim": self.symbol_embed_dim,
            "length_bucket_n_buckets": self.length_bucket_n_buckets,
            "pool_mode": self.pool_mode,
            "head_mode": self.head_mode,
        }


# ---------------------------------------------------------------------------
# TCN building blocks
# ---------------------------------------------------------------------------


class _CausalConv1d(nn.Module):
    """Conv1d with left-only (causal) padding so output length == input length."""

    def __init__(self, in_ch: int, out_ch: int, kernel_size: int, dilation: int) -> None:
        super().__init__()
        self.pad_len = (kernel_size - 1) * dilation
        self.conv = nn.Conv1d(in_ch, out_ch, kernel_size, dilation=dilation)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, C, T)
        x = F.pad(x, (self.pad_len, 0))
        return self.conv(x)


class _TCNResidualBlock(nn.Module):
    """Two causal convolutions with a residual skip connection.

    x → CausalConv → ReLU → Dropout → CausalConv → (+residual) → ReLU
    """

    def __init__(
        self, in_ch: int, out_ch: int, kernel_size: int, dilation: int, dropout: float
    ) -> None:
        super().__init__()
        self.conv1 = _CausalConv1d(in_ch, out_ch, kernel_size, dilation)
        self.conv2 = _CausalConv1d(out_ch, out_ch, kernel_size, dilation)
        self.drop = nn.Dropout(dropout)
        self.skip = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.skip(x)
        out = self.drop(torch.relu(self.conv1(x)))
        out = self.conv2(out)
        return torch.relu(out + residual)


class _TCNBody(nn.Module):
    """Input → transpose → L residual blocks → masked global avg pool → Linear → scalar."""

    def __init__(
        self,
        input_dim: int,
        n_channels: list[int],
        kernel_size: int = 7,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        ch_in = input_dim
        for i, ch_out in enumerate(n_channels):
            dilation = 2 ** i
            layers.append(_TCNResidualBlock(ch_in, ch_out, kernel_size, dilation, dropout))
            ch_in = ch_out
        self.blocks = nn.ModuleList(layers)
        self.head = nn.Linear(n_channels[-1], 1)
        self._init_weights()

    def _init_weights(self) -> None:
        for m in self.modules():
            if isinstance(m, nn.Conv1d):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        # x: (B, T, F) → (B, F, T)
        h = x.transpose(1, 2)
        for block in self.blocks:
            h = block(h)
        # Masked global average pool over the time axis.
        # h: (B, C, T)
        T = h.shape[2]
        arange = torch.arange(T, device=h.device).unsqueeze(0)  # (1, T)
        mask = arange < lengths.to(h.device).unsqueeze(1)  # (B, T)
        mask_f = mask.unsqueeze(1).float()  # (B, 1, T)
        pooled = (h * mask_f).sum(dim=2) / mask_f.sum(dim=2).clamp(min=1.0)  # (B, C)
        return self.head(pooled).squeeze(-1)  # (B,)


# ---------------------------------------------------------------------------
# TCN model class
# ---------------------------------------------------------------------------


@register_model("tcn")
class TCNVolModel(_BaseModel):
    """Temporal Convolutional Network for RV forecasting.

    Dilated causal convolutions over intraday bar sequences, producing a
    single log-RV prediction per day. Mirrors the ``LSTMVolModel`` API so
    the runner can dispatch interchangeably.
    """

    REQUIRED_LAYERS: list[str] = []
    requires_sequences: bool = True
    supports_tuning: bool = False
    name = "tcn"
    family = "tcn"
    description = "TCN sequence model with dilated causal convolutions"

    def __init__(
        self,
        *,
        input_dim: int,
        n_channels: list[int] | None = None,
        kernel_size: int = 7,
        dropout: float = 0.2,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        max_epochs: int = 100,
        batch_size: int = 32,
        val_fraction: float = 0.15,
        early_stopping_rounds: int | None = 5,
        val_purge_gap: int = 1,
        loss: str = "qlike",
        device: str = "auto",
        precision: str = "auto",
        seed: int = 42,
    ) -> None:
        if loss not in _LOSSES:
            raise ValueError(f"Unknown loss {loss!r}; expected one of {list(_LOSSES)}")
        if val_fraction < 0 or val_fraction >= 1:
            raise ValueError(f"val_fraction must be in [0, 1), got {val_fraction}")

        self.input_dim = int(input_dim)
        self.n_channels = list(n_channels) if n_channels is not None else [64, 64, 32]
        self.kernel_size = int(kernel_size)
        self.dropout = float(dropout)
        self.learning_rate = float(learning_rate)
        self.weight_decay = float(weight_decay)
        self.max_epochs = int(max_epochs)
        self.batch_size = int(batch_size)
        self.val_fraction = float(val_fraction)
        self.early_stopping_rounds = int(early_stopping_rounds) if early_stopping_rounds else 0
        self.val_purge_gap = int(val_purge_gap)
        self.loss = loss
        self.device = _resolve_device(device)
        self.precision = precision
        self.seed = int(seed)

        self._module: nn.Module | None = None
        self.epochs_run_: int = 0
        self.best_val_loss_: float | None = None
        self.history_: list[dict[str, float]] = []

    # ---- helpers ---------------------------------------------------------

    def _set_seed(self) -> None:
        torch.manual_seed(self.seed)
        if self.device == "cuda":
            torch.cuda.manual_seed_all(self.seed)

    def _build_module(self) -> nn.Module:
        return _TCNBody(
            input_dim=self.input_dim,
            n_channels=self.n_channels,
            kernel_size=self.kernel_size,
            dropout=self.dropout,
        ).to(self.device)

    def _align_targets(
        self, seq: SequenceTensor, y: pd.Series | np.ndarray
    ) -> tuple[torch.Tensor, np.ndarray]:
        if isinstance(y, pd.Series):
            aligned = y.reindex(seq.dates)
        else:
            arr = np.asarray(y, dtype=np.float32)
            if arr.shape[0] != len(seq):
                raise ValueError(f"Target length {arr.shape[0]} != seq length {len(seq)}")
            aligned = pd.Series(arr, index=seq.dates)
        finite_mask = aligned.notna().values
        y_kept = aligned.values[finite_mask].astype(np.float32)
        return torch.from_numpy(y_kept), finite_mask

    # ---- training --------------------------------------------------------

    def fit(
        self,
        seq: SequenceTensor,
        y: pd.Series | np.ndarray,
        *,
        base_preds: np.ndarray | torch.Tensor | pd.Series | None = None,
        symbol_ids: np.ndarray | torch.Tensor | None = None,
        on_progress: Any | None = None,
        on_batch_progress: Any | None = None,
    ) -> TCNVolModel:
        """Train on ``seq`` with target ``y`` (one log-RV per date)."""
        if seq.n_features != self.input_dim:
            raise ValueError(f"input_dim={self.input_dim} but seq has {seq.n_features} features")
        self._set_seed()

        if self.device.startswith("cuda"):
            torch.set_float32_matmul_precision("high")
            torch.backends.cudnn.benchmark = True

        # Align targets (log-transform, NaN mask)
        y_tensor, finite_mask = self._align_targets(seq, y)
        kept_idx = torch.from_numpy(np.where(finite_mask)[0]).to(torch.long)
        X = seq.tensor.index_select(0, kept_idx)
        L = seq.lengths.index_select(0, kept_idx)

        # Date-aware train/val split
        dates_kept = seq.dates.values[finite_mask]
        train_pos, val_pos = _split_train_val_by_date(dates_kept, self.val_fraction)

        # Date-level purge gap
        if self.val_purge_gap > 0 and len(train_pos) > 0 and len(val_pos) > 0:
            train_dates_arr = dates_kept[train_pos]
            unique_train_dates = np.sort(np.unique(train_dates_arr))
            purge_n = min(int(self.val_purge_gap), len(unique_train_dates) // 2)
            if purge_n > 0:
                purge_dates = set(unique_train_dates[-purge_n:].tolist())
                keep_mask = np.array(
                    [d not in purge_dates for d in train_dates_arr], dtype=bool
                )
                train_pos = train_pos[keep_mask]

        if (
            len(val_pos) > 0
            and len(train_pos) > 0
            and self.early_stopping_rounds > 0
        ):
            train_idx_t = torch.from_numpy(train_pos)
            val_idx_t = torch.from_numpy(val_pos)
            X_tr = X.index_select(0, train_idx_t)
            X_va = X.index_select(0, val_idx_t)
            L_tr = L.index_select(0, train_idx_t)
            L_va = L.index_select(0, val_idx_t)
            y_tr = y_tensor.index_select(0, train_idx_t)
            y_va = y_tensor.index_select(0, val_idx_t)
            use_val = True
        else:
            X_tr, L_tr, y_tr = X, L, y_tensor
            X_va = L_va = y_va = None
            use_val = False

        n_train = X_tr.shape[0]

        # Move training data to device
        if self.device != "cpu":
            X_tr = X_tr.to(self.device)
            y_tr = y_tr.to(self.device)
            if use_val:
                X_va = X_va.to(self.device)
                y_va = y_va.to(self.device)

        body = self._build_module()
        self._module = body
        opt = torch.optim.AdamW(
            body.parameters(),
            lr=self.learning_rate,
            weight_decay=self.weight_decay,
        )
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            opt, mode="min", factor=0.5, patience=2
        )
        criterion = _LOSSES[self.loss]
        autocast_dtype = _resolve_precision(self.precision, self.device)

        logger.info(
            "TCN fit: device=%s params=%d train=%d val=%d loss=%s",
            self.device,
            sum(p.numel() for p in body.parameters()),
            n_train,
            X_va.shape[0] if use_val else 0,
            self.loss,
        )

        best_val = math.inf
        bad_epochs = 0
        best_state: dict[str, torch.Tensor] | None = None

        self.epochs_run_ = 0
        self.history_ = []
        total_batches_per_epoch = math.ceil(n_train / self.batch_size)
        batch_update_stride = max(1, total_batches_per_epoch // 20)

        for epoch in range(1, self.max_epochs + 1):
            body.train()
            train_loss_sum = torch.zeros((), device=self.device)
            n_batches = 0
            perm = torch.randperm(n_train)

            for start in range(0, n_train, self.batch_size):
                batch_idx = perm[start : start + self.batch_size]
                xb = X_tr[batch_idx]
                lb = L_tr[batch_idx]
                yb = y_tr[batch_idx]
                opt.zero_grad(set_to_none=True)

                if autocast_dtype is not None:
                    with torch.autocast(device_type=self.device, dtype=autocast_dtype):
                        pred = body(xb, lb)
                        loss = criterion(pred.float(), yb)
                else:
                    pred = body(xb, lb)
                    loss = criterion(pred, yb)

                loss.backward()
                torch.nn.utils.clip_grad_norm_(body.parameters(), max_norm=5.0)
                opt.step()
                train_loss_sum = train_loss_sum + loss.detach()
                n_batches += 1

                if on_batch_progress is not None and (
                    n_batches == 1
                    or n_batches == total_batches_per_epoch
                    or n_batches % batch_update_stride == 0
                ):
                    on_batch_progress(
                        n_batches, total_batches_per_epoch, epoch, self.max_epochs
                    )

            tr_loss = float(train_loss_sum.item() / n_batches) if n_batches else float("nan")
            entry: dict[str, float] = {"epoch": epoch, "train_loss": tr_loss}

            if use_val:
                val_loss = self._eval_loss(X_va, L_va, y_va, criterion, autocast_dtype)
                entry["val_loss"] = val_loss
                scheduler.step(val_loss)
                improved = val_loss + 1e-6 < best_val
                if improved:
                    best_val = val_loss
                    bad_epochs = 0
                    best_state = {k: v.detach().cpu().clone() for k, v in body.state_dict().items()}
                else:
                    bad_epochs += 1
                self.epochs_run_ = epoch
                self.history_.append(entry)
                if on_progress is not None:
                    on_progress(epoch, self.max_epochs)
                if self.early_stopping_rounds and bad_epochs >= self.early_stopping_rounds:
                    logger.info(
                        "TCN early stopping at epoch %d (best val=%.5f)",
                        epoch, best_val,
                    )
                    break
            else:
                self.epochs_run_ = epoch
                self.history_.append(entry)
                if on_progress is not None:
                    on_progress(epoch, self.max_epochs)

        if use_val and best_state is not None:
            body.load_state_dict(best_state)
            self.best_val_loss_ = best_val

        return self

    def _eval_loss(
        self,
        X: torch.Tensor,
        L: torch.Tensor,
        y: torch.Tensor,
        criterion,
        autocast_dtype: torch.dtype | None,
    ) -> float:
        body = self._module
        assert body is not None
        body.eval()
        loss_sum = torch.zeros((), device=self.device)
        n_batches = 0
        with torch.no_grad():
            for start in range(0, X.shape[0], self.batch_size):
                xb = X[start : start + self.batch_size]
                lb = L[start : start + self.batch_size]
                yb = y[start : start + self.batch_size]
                if autocast_dtype is not None:
                    with torch.autocast(device_type=self.device, dtype=autocast_dtype):
                        pred = body(xb, lb)
                        loss = criterion(pred.float(), yb)
                else:
                    pred = body(xb, lb)
                    loss = criterion(pred, yb)
                loss_sum = loss_sum + loss.detach()
                n_batches += 1
        return float(loss_sum.item() / n_batches) if n_batches else float("nan")

    # ---- inference -------------------------------------------------------

    def predict(
        self,
        seq: SequenceTensor,
        *,
        base_preds: np.ndarray | torch.Tensor | pd.Series | None = None,
        symbol_ids: np.ndarray | torch.Tensor | None = None,
    ) -> np.ndarray:
        """Predict log-RV for each row of ``seq``."""
        if self._module is None:
            raise RuntimeError("TCNVolModel.predict called before fit")
        body = self._module
        body.eval()
        autocast_dtype = _resolve_precision(self.precision, self.device)
        out_chunks: list[torch.Tensor] = []
        with torch.no_grad():
            for start in range(0, len(seq), self.batch_size):
                xb = seq.tensor[start : start + self.batch_size].to(self.device, non_blocking=True)
                lb = seq.lengths[start : start + self.batch_size]
                if autocast_dtype is not None:
                    with torch.autocast(device_type=self.device, dtype=autocast_dtype):
                        pred = body(xb, lb).float()
                else:
                    pred = body(xb, lb)
                out_chunks.append(pred.detach().cpu())
        preds = torch.cat(out_chunks, dim=0).numpy().astype(np.float32)
        # Clamp to prevent extreme log-RV predictions that overflow exp() in evaluation.
        np.clip(preds, -20.0, 5.0, out=preds)
        return preds

    # ---- params ----------------------------------------------------------

    def get_params(self) -> dict[str, Any]:
        return {
            "input_dim": self.input_dim,
            "n_channels": self.n_channels,
            "kernel_size": self.kernel_size,
            "dropout": self.dropout,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "max_epochs": self.max_epochs,
            "batch_size": self.batch_size,
            "val_fraction": self.val_fraction,
            "early_stopping_rounds": self.early_stopping_rounds,
            "val_purge_gap": self.val_purge_gap,
            "loss": self.loss,
            "device": self.device,
            "precision": self.precision,
            "seed": self.seed,
        }
