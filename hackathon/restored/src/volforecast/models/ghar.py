"""GHAR: linear graph-HAR (Zhang, Pu, Cucuringu & Dong 2025, eq. 6).

log-RV variant on the repo's pooled panel: per (date, node) design row
    [ asset one-hot alpha | own features x_i | neighbor aggregate (W x)_i ]
with W = O^-1/2 A O^-1/2 (undirected, 'sym') or D^-1 A ('row', for directed DY
graphs). beta/gamma are pooled across assets (2F slopes total); only the
intercept is asset-specific. A = 0 recovers pooled HAR exactly — the nesting
that makes the Plan-03 graph ablation attributable to the graph alone.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from volforecast.models._base import _BaseModel
from volforecast.registry import register_model


def _dense_w(edge_index, edge_attr, n: int, norm: str) -> np.ndarray:
    """Build dense weighted adjacency with normalization from sparse edge tensors."""
    a = np.zeros((n, n), dtype=np.float64)
    if edge_index.numel():
        src = edge_index[0].numpy()
        dst = edge_index[1].numpy()
        a[src, dst] = edge_attr.numpy().astype(np.float64)
    deg = a.sum(axis=1)
    safe = np.where(deg > 0, deg, 1.0)
    if norm == "row":
        return a / safe[:, None]
    # sym: D^{-1/2} A D^{-1/2}
    d_inv_sqrt = np.where(deg > 0, 1.0 / np.sqrt(safe), 0.0)
    return d_inv_sqrt[:, None] * a * d_inv_sqrt[None, :]


@register_model("ghar")
class GHARVolModel(_BaseModel):
    """Pooled-OLS graph HAR. Consumes Plan-02 graph-dict lists."""

    REQUIRED_LAYERS: list[str] = ["har_core"]
    requires_sequences = False
    requires_graph = True
    supports_tuning = False
    family = "gnn"
    description = "Linear graph HAR: pooled own + neighbor-aggregate features (OLS)"

    def __init__(self, *, input_dim: int, w_norm: str = "sym", seed: int = 42) -> None:
        if w_norm not in ("sym", "row"):
            raise ValueError(f"w_norm must be 'sym' or 'row', got {w_norm!r}")
        self.input_dim = int(input_dim)
        self.w_norm = w_norm
        self.seed = int(seed)
        self.intercepts_: np.ndarray | None = None
        self.coef_beta_: np.ndarray | None = None
        self.coef_gamma_: np.ndarray | None = None
        self._n_nodes: int | None = None

    def _design(self, graphs: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
        """Build design matrix and target vector from graph-dict list."""
        n = graphs[0]["x"].shape[0]
        f = self.input_dim
        eye = np.eye(n)
        rows, ys = [], []
        for g in graphs:
            x = np.asarray(g["x"], dtype=np.float64)[:, :f]
            w = _dense_w(g["edge_index"], g["edge_attr"], n, self.w_norm)
            wx = w @ x
            y = np.asarray(g["y"], dtype=np.float64)
            for i in range(n):
                rows.append(np.concatenate([eye[i], x[i], wx[i]]))
                ys.append(y[i])
        return np.asarray(rows), np.asarray(ys)

    def fit(
        self, graphs: list[dict[str, Any]], y: Any | None = None, *, on_progress=None
    ) -> "GHARVolModel":
        if not graphs:
            raise ValueError("GHAR: no graphs to fit")
        self._n_nodes = graphs[0]["x"].shape[0]
        design, target = self._design(graphs)
        valid = np.isfinite(target)
        coefs, *_ = np.linalg.lstsq(design[valid], target[valid], rcond=None)
        n, f = self._n_nodes, self.input_dim
        self.intercepts_ = coefs[:n]
        self.coef_beta_ = coefs[n : n + f]
        self.coef_gamma_ = coefs[n + f : n + 2 * f]
        if on_progress is not None:
            on_progress(1, 1)
        return self

    def predict(self, graphs: list[dict[str, Any]]) -> np.ndarray:
        if self.coef_beta_ is None:
            raise RuntimeError("predict called before fit")
        design, _ = self._design(graphs)
        coefs = np.concatenate([self.intercepts_, self.coef_beta_, self.coef_gamma_])
        return design @ coefs

    def get_params(self) -> dict[str, Any]:
        return {"input_dim": self.input_dim, "w_norm": self.w_norm, "seed": self.seed}

    @property
    def summary(self) -> dict[str, float]:
        if self.coef_beta_ is None:
            return {}
        out: dict[str, float] = {"alpha_mean": float(np.mean(self.intercepts_))}
        for k in range(self.input_dim):
            out[f"beta_f{k}"] = float(self.coef_beta_[k])
            out[f"gamma_f{k}"] = float(self.coef_gamma_[k])
        return out
