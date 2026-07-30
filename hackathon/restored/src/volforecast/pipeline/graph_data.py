"""Bridge from the pooled (date, symbol) panel to graph-dict datasets.

Produces the exact structure ``GNNVolModel.fit``/``predict`` consume
(models/gnn.py): one dict per date with node features in a FIXED universe
order, NaN features zeroed (isolated/missing nodes still flow through the
MLP head), NaN targets preserved (masked inside the model).
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import torch

from volforecast.graphs.base import GraphSnapshot

#: trial_068's node feature list — the default for all graph models.
DEFAULT_NODE_FEATURES: list[str] = [
    "log_rv_d", "log_rv_w", "log_rv_m", "signed_return_d", "abs_ret_d",
    "log_rs_negative_d", "log_jump_d", "log_bpv_d", "log_cont_d",
]


def graph_input_panel(
    panel_data: dict[str, pd.DataFrame], graph_cfg: Any, ohlcv_dir: Any = None
) -> pd.DataFrame:
    """Wide date x symbol frame the graph builders estimate on.

    input='returns'  -> OHLCV close-to-close log returns (corr/glasso/knn/factor families)
    input='log_rv'   -> log of the rv column from the per-symbol RV panels (dy)
    """
    if graph_cfg.input == "log_rv":
        cols = {
            sym: np.log(df["rv"].clip(lower=1e-20))
            for sym, df in panel_data.items()
            if "rv" in df.columns
        }
        wide = pd.DataFrame(cols).sort_index()
        wide.columns.name = "symbol"
        return wide
    from volforecast.models.gnn_adjacency import panel_returns_from_ohlcv
    from volforecast.utils.paths import ohlcv_cache_dir

    return panel_returns_from_ohlcv(ohlcv_dir or ohlcv_cache_dir())


def build_graph_dataset(
    X_panel: pd.DataFrame,
    y_panel: pd.Series | None,
    dates: list[Any],
    schedule: dict[Any, GraphSnapshot],
    node_feature_cols: list[str],
    symbols: list[str],
) -> list[dict[str, Any]]:
    """One graph dict per date. Node order == ``symbols`` order on every date.

    Returns list of dicts satisfying the GNNVolModel contract:
      - "x": (N, F) float32 numpy, NaN→0
      - "edge_index": (2, E) torch.long
      - "edge_attr": (E,) torch.float32
      - "y": (N,) float64 numpy, NaN preserved
      - "date": timestamp
    """
    missing = [c for c in node_feature_cols if c not in X_panel.columns]
    if missing:
        raise ValueError(f"node feature column(s) not in panel: {missing}")

    n, f = len(symbols), len(node_feature_cols)
    full_idx = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
    X_dense = X_panel[node_feature_cols].reindex(full_idx)
    x_all = X_dense.to_numpy(dtype=np.float32).reshape(len(dates), n, f)
    x_all = np.nan_to_num(x_all, nan=0.0)

    if y_panel is not None:
        y_all = y_panel.reindex(full_idx).to_numpy(dtype=np.float64).reshape(len(dates), n)
    else:
        y_all = np.full((len(dates), n), np.nan)

    graphs: list[dict[str, Any]] = []
    for i, date in enumerate(dates):
        snap = schedule[date]
        edge_index, edge_attr = snap.to_torch()
        graphs.append(
            {
                "x": x_all[i],
                "edge_index": edge_index,
                "edge_attr": edge_attr,
                "y": y_all[i],
                "date": date,
            }
        )
    return graphs


def augment_edge_features(
    graphs: list[dict[str, Any]], vov_idx: int
) -> list[dict[str, Any]]:
    """Widen edge_attr from (E,) to (E, 3): [weight, vov_src, vov_dst].

    Lifts per-node vol-of-vol values onto edges so attention scores can
    condition on endpoint volatility-of-volatility (SpotV2Net-style).

    Parameters
    ----------
    graphs : list[dict]
        Graph dicts from build_graph_dataset. edge_attr is (E,) float.
    vov_idx : int
        Column index of vov_d in the node feature matrix x.

    Returns
    -------
    list[dict] with edge_attr widened to (E, 3). NaN vov values are zero-filled.
    """
    out = []
    for g in graphs:
        ei = g["edge_index"]
        w = g["edge_attr"].float().reshape(-1)
        x = torch.from_numpy(g["x"]) if not isinstance(g["x"], torch.Tensor) else g["x"]
        if ei.numel():
            vov_src = x[ei[0], vov_idx].float()
            vov_dst = x[ei[1], vov_idx].float()
            # NaN was already zeroed in build_graph_dataset, but be safe
            vov_src = torch.nan_to_num(vov_src, nan=0.0)
            vov_dst = torch.nan_to_num(vov_dst, nan=0.0)
            attr = torch.stack([w, vov_src, vov_dst], dim=1)
        else:
            attr = torch.zeros(0, 3)
        out.append({**g, "edge_attr": attr})
    return out
