"""Graph diagnostics: density/degree stats, edge-set Jaccard, schedule stability.

Monitors two published failure modes: crisis density explosion of thresholded
correlation graphs (Wade 2026, Table 2) and GLASSO edge instability across
refits (O Nuallain 2025, section 5.5: consecutive-refit Jaccard dipping below 0.8).

Also provides the magnetic Laplacian (Chi, Gao & Wang 2024, arXiv 2410.22706,
eqs. 6-9; Shubin 1994) and graph signal energy diagnostics for GSP-HAR.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from volforecast.graphs.base import GraphSnapshot


# ---------------------------------------------------------------------------
# Magnetic Laplacian (Chi, Gao & Wang 2024, eqs. 6-9)
# ---------------------------------------------------------------------------


def magnetic_laplacian(w: np.ndarray, q: float = 0.25) -> np.ndarray:
    """Magnetic Laplacian L^(q) for a directed weighted adjacency matrix.

    L^(q) = I - (D_s^{-1/2} W_s D_s^{-1/2}) * exp(i 2 pi q (W - W^T))

    where W_s = (W + W^T) / 2, D_s = diag(W_s @ 1).
    Hermitian PSD with real non-negative eigenvalues.

    Parameters
    ----------
    w : (N, N) non-negative adjacency matrix (possibly directed/asymmetric).
    q : float >= 0, coupling between direction and phase. q=0 gives standard
        symmetric normalized Laplacian on W_s.

    Returns
    -------
    (N, N) complex128 Hermitian matrix.
    """
    n = w.shape[0]
    ws = 0.5 * (w + w.T)
    d = ws.sum(axis=1)
    inv_sqrt = np.where(d > 0, 1.0 / np.sqrt(np.where(d > 0, d, 1.0)), 0.0)
    norm = inv_sqrt[:, None] * ws * inv_sqrt[None, :]
    phase = np.exp(1j * 2.0 * np.pi * q * (w - w.T))
    lap = np.eye(n, dtype=np.complex128) - norm * phase
    return lap


def graph_signal_energy(snapshot: GraphSnapshot, x: np.ndarray, q: float = 0.0) -> float:
    """Graph signal energy (roughness) E(x) = Re(x^H L x).

    Measures how much the signal x varies across graph edges. Spikes in
    crises on informative spillover graphs; stays flat on uninformative ones.
    """
    w = snapshot.dense_adjacency()
    lap = magnetic_laplacian(w, q)
    xc = x.astype(np.complex128)
    return float(np.real(np.conj(xc) @ lap @ xc))


def energy_series(
    schedule: dict[Any, GraphSnapshot], panel: pd.DataFrame, q: float = 0.0
) -> pd.Series:
    """Per-date roughness of the cross-section over its point-in-time graph.

    Parameters
    ----------
    schedule : {date -> GraphSnapshot} mapping from build_graph_schedule.
    panel : DataFrame with DatetimeIndex and columns = symbols; values = log-RV.

    Returns
    -------
    pd.Series indexed by date with graph signal energy values.
    """
    energies: dict[Any, float] = {}
    for date in sorted(schedule):
        if date not in panel.index:
            continue
        snap = schedule[date]
        row = panel.loc[date]
        x = row.reindex(list(snap.symbols)).values.astype(np.float64)
        if np.any(~np.isfinite(x)):
            continue
        energies[date] = graph_signal_energy(snap, x, q)
    return pd.Series(energies, dtype=np.float64)


def _edge_set(s: GraphSnapshot) -> set[tuple[int, int]]:
    return {(int(i), int(j)) for i, j in zip(*s.edge_index)}


def snapshot_stats(s: GraphSnapshot) -> dict[str, Any]:
    out_deg = np.zeros(s.n_nodes, dtype=np.int64)
    if s.n_edges:
        out_deg = np.bincount(s.edge_index[0], minlength=s.n_nodes)
    return {
        "date": s.date,
        "method": s.method,
        "n_nodes": s.n_nodes,
        "n_edges": s.n_edges,
        "density": s.density(),
        "mean_degree": float(out_deg.mean()) if s.n_nodes else 0.0,
        "isolated_nodes": int((out_deg == 0).sum()),
    }


def edge_jaccard(a: GraphSnapshot, b: GraphSnapshot) -> float:
    ea, eb = _edge_set(a), _edge_set(b)
    union = ea | eb
    if not union:
        return 1.0
    return len(ea & eb) / len(union)


def schedule_stability(schedule: dict[Any, GraphSnapshot]) -> pd.DataFrame:
    """One row per unique snapshot (refit), with Jaccard vs the previous refit."""
    rows: list[dict[str, Any]] = []
    prev: GraphSnapshot | None = None
    seen: set[int] = set()
    for date in sorted(schedule):
        snap = schedule[date]
        if id(snap) in seen:
            continue
        seen.add(id(snap))
        row = snapshot_stats(snap)
        row["date"] = date
        row["jaccard_prev"] = np.nan if prev is None else edge_jaccard(prev, snap)
        rows.append(row)
        prev = snap
    return pd.DataFrame(rows)
