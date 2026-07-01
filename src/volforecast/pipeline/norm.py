"""Per-symbol sequence normalisation utilities.

When ``norm_mode="per_symbol"``, each symbol's rows are normalised using
statistics computed only from that symbol's training data. This avoids
blending regimes across symbols (e.g. NVDA's vol characteristics diluting
SPY's normaliser).

The default ``norm_mode="pooled"`` pools all symbols into a single
normaliser — acceptable when features are mostly bounded (like v2 features)
but sub-optimal for features with heterogeneous cross-symbol distributions.
"""

from __future__ import annotations

import torch


def fit_per_symbol_normaliser(
    tensor: torch.Tensor,
    lengths: torch.Tensor,
    symbol_ids: torch.Tensor,
    *,
    eps: float = 1e-6,
) -> dict[int, tuple[torch.Tensor, torch.Tensor]]:
    """Compute per-feature (mean, std) for EACH unique symbol_id.

    Parameters
    ----------
    tensor : torch.Tensor
        Shape ``(N, max_bars, n_features)`` — the training rows.
    lengths : torch.Tensor
        Shape ``(N,)`` int — valid bar counts per row.
    symbol_ids : torch.Tensor
        Shape ``(N,)`` int — symbol index per row.
    eps : float
        Minimum std clamp to avoid div-by-zero.

    Returns
    -------
    dict[int, tuple[torch.Tensor, torch.Tensor]]
        Mapping ``symbol_id -> (mean, std)`` where each is shape ``(n_features,)``.
    """
    unique_ids = torch.unique(symbol_ids)
    n_features = tensor.shape[2]
    max_bars = tensor.shape[1]
    normalisers: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}

    arange = torch.arange(max_bars).unsqueeze(0)  # (1, max_bars)

    for sid in unique_ids:
        sid_val = int(sid.item())
        mask = symbol_ids == sid
        subset = tensor[mask]  # (n_sym, max_bars, n_feat)
        sub_lens = lengths[mask]  # (n_sym,)

        # Build valid-bar mask: (n_sym, max_bars)
        valid_2d = arange < sub_lens.unsqueeze(1)
        valid_3d = valid_2d.unsqueeze(-1).expand_as(subset)

        counts = valid_2d.sum().to(torch.float64).item()
        if counts <= 1:
            # Degenerate — use zeros/ones
            normalisers[sid_val] = (
                torch.zeros(n_features, dtype=torch.float32),
                torch.ones(n_features, dtype=torch.float32),
            )
            continue

        x = subset.to(torch.float64)
        masked = torch.where(valid_3d, x, torch.zeros_like(x))
        sums = masked.sum(dim=(0, 1))  # (n_feat,)
        mean = sums / counts

        sq = torch.where(valid_3d, (x - mean) ** 2, torch.zeros_like(x))
        var = sq.sum(dim=(0, 1)) / counts
        std = var.sqrt().to(torch.float32).clamp_min(eps)
        mean = mean.to(torch.float32)
        normalisers[sid_val] = (mean, std)

    return normalisers


def apply_per_symbol_normaliser(
    tensor: torch.Tensor,
    lengths: torch.Tensor,
    symbol_ids: torch.Tensor,
    normalisers: dict[int, tuple[torch.Tensor, torch.Tensor]],
) -> torch.Tensor:
    """Apply per-symbol z-score normalisation and re-zero pad positions.

    Parameters
    ----------
    tensor : torch.Tensor
        Shape ``(N, max_bars, n_features)``.
    lengths : torch.Tensor
        Shape ``(N,)`` int.
    symbol_ids : torch.Tensor
        Shape ``(N,)`` int.
    normalisers : dict
        From :func:`fit_per_symbol_normaliser`.

    Returns
    -------
    torch.Tensor
        Normalised tensor, same shape as input, with pad positions zeroed.
    """
    normed = tensor.clone()
    max_bars = tensor.shape[1]
    arange = torch.arange(max_bars).unsqueeze(0)  # (1, max_bars)

    for sid_val, (mean, std) in normalisers.items():
        mask = symbol_ids == sid_val
        if not mask.any():
            continue
        normed[mask] = (tensor[mask] - mean) / std

    # Re-zero pad positions
    valid_2d = arange < lengths.unsqueeze(1)  # (N, max_bars)
    pad_mask_3d = (~valid_2d).unsqueeze(-1).expand_as(normed)
    normed = normed.masked_fill(pad_mask_3d, 0.0)

    return normed
