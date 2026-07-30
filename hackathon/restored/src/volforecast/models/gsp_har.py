"""GSP-HAR: Graph Signal Processing HAR with magnetic Laplacian spectral filter.

Chi, Gao & Wang (2024), arXiv 2410.22706. Per refit-block, eigendecompose
L^(q) once. Graph channel: g = Re(U diag(h_re + i*h_im) U^H X) — a learnable
complex spectral filter applied to the cross-section — then
y_hat = alpha + X*beta + g*gamma.

Empty graph: L = I → U = I, filter on identity basis; h initialized to 0 so
the channel starts at zero and the model nests QLIKE-HAR at initialization.
"""

from __future__ import annotations

import logging
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn

from volforecast.graphs.diagnostics import magnetic_laplacian
from volforecast.models._base import _BaseModel
from volforecast.models.gnn import _LOSSES, _resolve_device, _resolve_precision
from volforecast.registry import register_model

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PyTorch Module
# ---------------------------------------------------------------------------


class _GSPHARModule(nn.Module):
    """Spectral filter on pre-computed eigenvectors + linear HAR readout."""

    def __init__(self, n_nodes: int, input_dim: int) -> None:
        super().__init__()
        self.h_re = nn.Parameter(torch.zeros(n_nodes))
        self.h_im = nn.Parameter(torch.zeros(n_nodes))
        self.alpha = nn.Parameter(torch.zeros(n_nodes))
        self.beta = nn.Linear(input_dim, 1, bias=False)
        self.gamma = nn.Linear(input_dim, 1, bias=False)

    def forward(self, x: torch.Tensor, u: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x : (T, N, F) real node features
        u : (N, N) complex eigenvector matrix (same for all T in a refit block)

        Returns
        -------
        (T, N) per-node predictions
        """
        t_len = x.shape[0]
        xc = x.to(torch.complex64)
        # GFT: project onto eigenvectors
        # u: (N, N), x: (T, N, F) -> x_hat: (T, N, F)
        u_h = u.conj().T  # (N, N)
        x_hat = torch.einsum("ij,tjf->tif", u_h, xc)
        # Apply learnable complex spectral filter
        filt = (self.h_re + 1j * self.h_im).unsqueeze(0).unsqueeze(-1)  # (1, N, 1)
        # Inverse GFT
        g = torch.einsum("ij,tjf->tif", u, x_hat * filt).real  # (T, N, F)
        # Readout
        return self.alpha[None, :] + self.beta(x).squeeze(-1) + self.gamma(g).squeeze(-1)


# ---------------------------------------------------------------------------
# Helper: build dense W and cache eigendecomposition
# ---------------------------------------------------------------------------


def _build_dense_from_graph(graph: dict[str, Any], n: int) -> np.ndarray:
    """Build dense (N, N) adjacency from a graph dict."""
    ei, ea = graph["edge_index"], graph["edge_attr"]
    a = np.zeros((n, n), dtype=np.float64)
    if hasattr(ei, "numpy"):
        ei = ei.numpy()
    if hasattr(ea, "numpy"):
        ea = ea.numpy()
    if ei.size > 0:
        a[ei[0], ei[1]] = ea.astype(np.float64)
    return a


# ---------------------------------------------------------------------------
# Registered model class
# ---------------------------------------------------------------------------


@register_model("gsp_har")
class GSPHARVolModel(_BaseModel):
    """GSP-HAR: magnetic Laplacian spectral model + linear HAR channel.

    Eigendecomposition is computed once per unique graph snapshot (cached by
    the graph dict's edge_index object identity, which is stable within a
    refit block per the Plan-01 schedule contract).
    """

    REQUIRED_LAYERS: list[str] = ["har_core"]
    requires_sequences: bool = False
    requires_graph: bool = True
    supports_tuning: bool = False
    family = "gnn"
    description = "GSP-HAR: magnetic Laplacian spectral filter + linear HAR channel"

    def __init__(
        self,
        *,
        input_dim: int,
        q: float = 0.25,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        max_epochs: int = 300,
        early_stopping_rounds: int = 25,
        val_fraction: float = 0.15,
        loss: str = "qlike",
        n_seeds: int = 3,
        device: str = "auto",
        precision: str = "auto",
        seed: int = 42,
    ) -> None:
        if loss not in _LOSSES:
            raise ValueError(f"Unknown loss {loss!r}; expected one of {list(_LOSSES)}")
        self.input_dim = int(input_dim)
        self.q = float(q)
        self.learning_rate = float(learning_rate)
        self.weight_decay = float(weight_decay)
        self.max_epochs = int(max_epochs)
        self.early_stopping_rounds = int(early_stopping_rounds)
        self.val_fraction = float(val_fraction)
        self.loss = loss
        self.n_seeds = int(n_seeds)
        self.device = _resolve_device(device)
        self.precision = precision
        self.seed = int(seed)

        self._modules_: list[_GSPHARModule] = []
        self._n_nodes: int | None = None
        self.epochs_run_: int = 0
        self.best_val_loss_: float | None = None
        self._eigh_cache: dict[tuple[bytes, bytes], torch.Tensor] = {}
        self._eigh_count: int = 0  # for testing: how many decompositions computed

    def _set_seed(self, seed: int) -> None:
        torch.manual_seed(seed)
        np.random.seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

    def _get_eigenvectors(self, graph: dict[str, Any], n: int) -> torch.Tensor:
        """Get (N, N) complex eigenvector matrix, caching by edge content."""
        ei = graph["edge_index"]
        ea = graph["edge_attr"]
        # Cache key: bytes of edge_index + edge_attr
        ei_np = ei.numpy() if hasattr(ei, "numpy") else np.asarray(ei)
        ea_np = ea.numpy() if hasattr(ea, "numpy") else np.asarray(ea)
        key = (ei_np.tobytes(), ea_np.tobytes())
        if key not in self._eigh_cache:
            w = _build_dense_from_graph(graph, n)
            lap = magnetic_laplacian(w, self.q)
            _, vecs = np.linalg.eigh(lap)
            self._eigh_cache[key] = torch.from_numpy(vecs).to(torch.complex64)
            self._eigh_count += 1
        return self._eigh_cache[key]

    # ------------------------------------------------------------------
    # fit
    # ------------------------------------------------------------------

    def fit(
        self,
        graphs: list[dict[str, Any]],
        y: Any | None = None,
        *,
        on_progress: Any | None = None,
    ) -> "GSPHARVolModel":
        """Train GSP-HAR on a list of graph snapshots.

        Parameters
        ----------
        graphs : list[dict]
            Each dict: "x" (N, F), "edge_index" (2, E), "edge_attr" (E,), "y" (N,), "date".
        """
        if not graphs:
            raise ValueError("GSP-HAR: no graphs to fit")

        n = graphs[0]["x"].shape[0]
        f = self.input_dim
        self._n_nodes = n
        self._eigh_cache.clear()
        self._eigh_count = 0

        # Stack data tensors
        X = torch.tensor(
            np.stack([g["x"][:, :f] for g in graphs]), dtype=torch.float32
        )  # (T, N, F)
        Y = torch.tensor(np.stack([g["y"] for g in graphs]), dtype=torch.float32)  # (T, N)
        mask = torch.isfinite(Y)

        # Group by unique graph snapshot (edge_index identity)
        # For GSP-HAR, all dates sharing the same snapshot share eigenvectors.
        # We'll compute U per snapshot and assign to each date.
        U_list: list[torch.Tensor] = []
        for g in graphs:
            U_list.append(self._get_eigenvectors(g, n))

        # For training we use a single U per date (they share within refit blocks)
        # Stack into (T, N, N) complex
        U_stack = torch.stack(U_list)  # (T, N, N)

        # Temporal val split
        t_total = len(graphs)
        n_val = max(1, int(math.ceil(t_total * self.val_fraction)))
        n_train = t_total - n_val

        X_tr, X_val = X[:n_train], X[n_train:]
        Y_tr, Y_val = Y[:n_train], Y[n_train:]
        U_tr, U_val = U_stack[:n_train], U_stack[n_train:]
        mask_tr, mask_val = mask[:n_train], mask[n_train:]

        # Move to device
        dev = self.device
        X_tr, X_val = X_tr.to(dev), X_val.to(dev)
        Y_tr, Y_val = Y_tr.to(dev), Y_val.to(dev)
        U_tr, U_val = U_tr.to(dev), U_val.to(dev)
        mask_tr, mask_val = mask_tr.to(dev), mask_val.to(dev)

        amp_dtype = _resolve_precision(self.precision, dev)
        criterion = _LOSSES[self.loss]
        total_epochs = self.n_seeds * self.max_epochs
        global_epoch = 0
        val_losses_all = []

        self._modules_ = []

        for s in range(self.n_seeds):
            self._set_seed(self.seed + s)
            module = _GSPHARModule(n, f).to(dev)
            optimizer = torch.optim.Adam(
                module.parameters(), lr=self.learning_rate, weight_decay=self.weight_decay
            )

            best_val_loss = float("inf")
            patience_counter = 0
            best_state: dict[str, Any] | None = None

            for epoch in range(1, self.max_epochs + 1):
                global_epoch += 1

                # --- Train ---
                module.train()
                optimizer.zero_grad()

                # For efficiency: if all dates share one U, broadcast; otherwise per-date
                # Use unique U approach: since U varies across refit blocks, we use per-date
                # forward with the full U_tr tensor
                # The module needs a single U; we process by unique blocks
                pred = self._forward_batched(module, X_tr, U_tr)
                loss = criterion(pred[mask_tr], Y_tr[mask_tr])
                loss.backward()
                torch.nn.utils.clip_grad_norm_(module.parameters(), 1.0)
                optimizer.step()

                # --- Validate ---
                module.eval()
                with torch.no_grad():
                    val_pred = self._forward_batched(module, X_val, U_val)
                    val_loss = criterion(val_pred[mask_val], Y_val[mask_val]).item()

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    best_state = {
                        k: v.detach().cpu().clone() for k, v in module.state_dict().items()
                    }
                else:
                    patience_counter += 1

                if on_progress is not None:
                    on_progress(global_epoch, total_epochs)

                if patience_counter >= self.early_stopping_rounds:
                    remaining = self.max_epochs - epoch
                    global_epoch += remaining
                    if on_progress is not None and remaining > 0:
                        on_progress(global_epoch, total_epochs)
                    break

            if best_state is not None:
                module.load_state_dict(best_state)
                module.to(dev)
            module.eval()
            self._modules_.append(module)
            val_losses_all.append(best_val_loss)

        self.epochs_run_ = global_epoch
        self.best_val_loss_ = float(np.mean(val_losses_all))
        return self

    @staticmethod
    def _forward_batched(
        module: _GSPHARModule, x: torch.Tensor, u_stack: torch.Tensor
    ) -> torch.Tensor:
        """Forward pass handling potentially different U per date.

        If all U are the same (single refit block), use efficient single-U path.
        Otherwise, iterate over unique U groups.
        """
        # Check if all U in the stack are the same (same refit block)
        # Optimization: compare first and last
        if u_stack.shape[0] <= 1 or torch.equal(u_stack[0], u_stack[-1]):
            return module(x, u_stack[0])
        # General case: group by unique U and forward each group
        # For training this is acceptable since refit blocks are large
        results = []
        for t in range(x.shape[0]):
            results.append(module(x[t:t+1], u_stack[t]))
        return torch.cat(results, dim=0)

    # ------------------------------------------------------------------
    # _graph_channel: spectral contribution only (for nesting test)
    # ------------------------------------------------------------------

    def _graph_channel(self, graphs: list[dict[str, Any]]) -> np.ndarray:
        """Return only the gamma-channel output (zero when h=0)."""
        if not self._modules_:
            raise RuntimeError("_graph_channel called before fit")
        n = self._n_nodes
        f = self.input_dim
        X = torch.tensor(
            np.stack([g["x"][:, :f] for g in graphs]), dtype=torch.float32
        )
        U_list = [self._get_eigenvectors(g, n) for g in graphs]
        U_stack = torch.stack(U_list)
        dev = self.device
        X, U_stack = X.to(dev), U_stack.to(dev)

        contribs = []
        for module in self._modules_:
            module.eval()
            with torch.no_grad():
                xc = X.to(torch.complex64)
                u = U_stack[0] if U_stack.shape[0] == 1 else U_stack[0]
                u_h = u.conj().T
                x_hat = torch.einsum("ij,tjf->tif", u_h, xc)
                filt = (module.h_re + 1j * module.h_im).unsqueeze(0).unsqueeze(-1)
                g = torch.einsum("ij,tjf->tif", u, x_hat * filt).real
                contrib = module.gamma(g).squeeze(-1)
            contribs.append(contrib.cpu().numpy())
        return np.mean(contribs, axis=0)

    # ------------------------------------------------------------------
    # predict
    # ------------------------------------------------------------------

    def predict(self, graphs: list[dict[str, Any]]) -> np.ndarray:
        """Predict log-RV for each node in each graph.

        Returns
        -------
        np.ndarray, shape (T*N,) — predictions flattened node-major per date.
        """
        if not self._modules_:
            raise RuntimeError("predict called before fit")
        n = self._n_nodes
        f = self.input_dim
        X = torch.tensor(
            np.stack([g["x"][:, :f] for g in graphs]), dtype=torch.float32
        )
        U_list = [self._get_eigenvectors(g, n) for g in graphs]
        U_stack = torch.stack(U_list)
        dev = self.device
        X, U_stack = X.to(dev), U_stack.to(dev)

        preds = []
        for module in self._modules_:
            module.eval()
            with torch.no_grad():
                pred = self._forward_batched(module, X, U_stack)
            preds.append(pred.cpu().numpy())
        return np.mean(preds, axis=0).reshape(-1)

    # ------------------------------------------------------------------
    # extract_features
    # ------------------------------------------------------------------

    def extract_features(
        self,
        graphs: list[dict[str, Any]],
        *,
        outputs: list[str] | None = None,
    ) -> dict[str, np.ndarray]:
        if outputs is None:
            outputs = ["prediction"]
        result: dict[str, np.ndarray] = {}
        if "prediction" in outputs:
            result["prediction"] = self.predict(graphs)
        return result

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    def save(self, path: Path) -> Path:
        if not self._modules_:
            raise RuntimeError("GSPHARVolModel.save called before fit")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "init_kwargs": self.get_params(),
            "state_dicts": [
                {k: v.detach().cpu() for k, v in m.state_dict().items()}
                for m in self._modules_
            ],
            "n_nodes": self._n_nodes,
            "epochs_run": self.epochs_run_,
            "best_val_loss": self.best_val_loss_,
        }
        tmp = path.with_suffix(path.suffix + ".tmp")
        torch.save(payload, tmp)
        os.replace(tmp, path)
        return path

    @classmethod
    def load(cls, path: Path) -> "GSPHARVolModel":
        payload = torch.load(Path(path), map_location="cpu", weights_only=False)
        instance = cls(**payload["init_kwargs"])
        instance._n_nodes = payload["n_nodes"]
        n = instance._n_nodes
        f = instance.input_dim
        instance._modules_ = []
        for sd in payload["state_dicts"]:
            module = _GSPHARModule(n, f)
            module.load_state_dict(sd)
            module.eval()
            instance._modules_.append(module)
        instance.epochs_run_ = payload.get("epochs_run", 0)
        instance.best_val_loss_ = payload.get("best_val_loss")
        return instance

    # ------------------------------------------------------------------
    # params / summary
    # ------------------------------------------------------------------

    def get_params(self) -> dict[str, Any]:
        return {
            "input_dim": self.input_dim,
            "q": self.q,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "max_epochs": self.max_epochs,
            "early_stopping_rounds": self.early_stopping_rounds,
            "val_fraction": self.val_fraction,
            "loss": self.loss,
            "n_seeds": self.n_seeds,
            "device": self.device,
            "precision": self.precision,
            "seed": self.seed,
        }

    def get_arch_summary(self) -> dict[str, Any]:
        param_count = None
        if self._modules_:
            param_count = sum(p.numel() for p in self._modules_[0].parameters())
        return {
            "q": self.q,
            "n_seeds": self.n_seeds,
            "loss": self.loss,
            "epochs_trained": self.epochs_run_,
            "best_val_loss": self.best_val_loss_,
            "param_count": param_count,
            "eigh_decompositions": self._eigh_count,
        }

    @property
    def summary(self) -> dict[str, float]:
        s = self.get_arch_summary()
        return {k: float(v) for k, v in s.items() if v is not None and isinstance(v, (int, float))}
