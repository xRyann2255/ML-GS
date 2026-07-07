# Plan 05 — Attention Upgrades: Edge Features, Graph Transformer, Spillover Export

> **For the Copilot orchestrator:** execute with `/execute` (§6). TDD hard gate. Requires Plans 01–04 merged. This plan tests a **hypothesis with no published confirmation**: "no vol paper has yet shown, under QLIKE with significance tests, that the attention upgrade beats fixed weights" (chapter §Attention). A null result is a finding.

**Goal:** Upgrade the existing GATv2 (`models/gnn.py`) along the three attention frontiers the literature motivates: (1) **SpotV2Net-style edge features** — second-order vol-of-vol quantities entering the attention scores (Brini & Toscano 2024: "graph topology can be trivial when the features are rich"); (2) **UniMP/TransformerConv** option — scaled dot-product attention with a linear self-term (GTN-VF, Chen & Robert 2022, whose relation-free variant *lost to HAR* — relational information earns the win, not DL machinery); (3) **attention→spillover matrix export** — the learned, state-dependent analogue of the DY table (with the explicit caveat: trained parameters that co-move with regimes, *not* identified causal spillovers; and the SpotV2Net/GNNExplainer warning that interpretability output can reflect training-period idiosyncrasies).

**Architecture:** All three are parameters of the existing `GNNVolModel` — no new registry names. `conv_type: "gatv2" | "transformer"` selects `GATv2Conv` vs `TransformerConv` (both accept `edge_dim`); `graph_data.augment_edge_features` widens `edge_attr` from `(E,)` to `(E, 3)` = `[weight, vov_src, vov_dst]` pulled from a per-symbol vol-of-vol node column supplied by a new tiny feature layer; `spillover_matrix()` aggregates layer-2 attention into a dst-normalized N×N DataFrame. **Characterization first:** default params must reproduce current behavior bit-for-bit.

**Tech stack:** `torch_geometric.nn.TransformerConv` (already in the `graph` extra — UniMP operator). New feature layer uses pandas only. No new dependencies.

## Global constraints

As 00-overview §4.1. Plan-specific:
- **Zero behavior change at defaults** (`conv_type="gatv2"`, scalar edge weights): characterization test pins predictions of a fixed-seed fit before/after the refactor.
- Directed graphs (DY) must work through both conv types (PyG treats `edge_index` as directed already — test it).
- The vol-of-vol feature must be strictly lagged (built from `log_rv_d`, which is already shifted).

## File map

| Action | Path | Responsibility |
|---|---|---|
| Create | `src/volforecast/features/vol_of_vol.py` | `vov_d`, `vov_w` per-symbol columns |
| Modify | `src/volforecast/registry.py` | feature import |
| Modify | `src/volforecast/models/gnn.py` | `conv_type`, `edge_dim` handling, `spillover_matrix()` |
| Modify | `src/volforecast/pipeline/graph_data.py` | `augment_edge_features` + wiring flag |
| Modify | `src/volforecast/config.py` | `GraphConfig.edge_features: str = "weight"` (`"weight"|"volofvol"`) |
| Modify | `workspace/configs/_CANONICAL_EXAMPLE.yaml` | document both knobs |
| Create | `src/tests/unit/test_vol_of_vol.py`, `src/tests/unit/test_gnn_attention.py` | tests |
| Create | `workspace/configs/trial_083_attention_upgrades.yaml` | the hypothesis experiment |

---

## Task 1: `vol_of_vol` feature layer

**Copilot context packet:**

```yaml
subtask_id: "gnn-05-1"
goal: "Add a 'vol_of_vol' feature layer producing vov_d (22d rolling std of log_rv_d) and vov_w (5d mean of vov_d), registered in FEATURE_REGISTRY, with no-lookahead tests."
file_scope:
  - workspace/plans/gnn/plan-05-attention-upgrades.md
  - src/volforecast/features/noise_robust.py     # smallest existing layer as the pattern
  - src/volforecast/features/transforms.py
  - src/volforecast/registry.py
write_scope:
  - src/volforecast/features/vol_of_vol.py
  - src/volforecast/registry.py
  - src/tests/unit/test_vol_of_vol.py
acceptance_criteria:
  - "./vol test -k test_vol_of_vol -> pass"
  - "vov_d at t depends only on log_rv values dated <= t (perturbation test on future rows)"
  - "Layer registered as 'vol_of_vol'; compute(daily_data, *, context=None) contract honored"
constraints: ["TDD failing-first", "vov_d = rolling(22).std() of log(rv).shift(1) — the shift(1) BEFORE rolling (look-ahead checklist)", "Update _CANONICAL_EXAMPLE.yaml feature_layers comment"]
context_summary: |
  SpotV2Net's edge features are vol-of-vol quantities. Our daily proxy: trailing 22d std of
  lagged daily log-RV per symbol. Emitted as node-feature columns so graph_data can lift them
  onto edges; also usable by tree models directly. Follow the standard layer class shape
  (@register_feature_layer, compute(daily_data, *, context=None) -> DataFrame).
depends_on: []
```

Test essentials (`test_vol_of_vol.py`): columns `{vov_d, vov_w}` exist; first ~23 rows NaN; perturbing `rv` at dates > t leaves `vov_d[t]` unchanged; layer in `FEATURE_REGISTRY`. Implementation:

```python
@register_feature_layer("vol_of_vol")
class VolOfVolLayer:
    """Trailing vol-of-vol: 22d std of lagged daily log-RV (SpotV2Net edge-feature proxy)."""

    def compute(self, daily_data: pd.DataFrame, *, context=None) -> pd.DataFrame:
        log_rv_lag = safe_log(daily_data["rv"]).shift(1)
        vov_d = log_rv_lag.rolling(22).std()
        return pd.DataFrame({"vov_d": vov_d, "vov_w": vov_d.rolling(5).mean()},
                            index=daily_data.index)
```

Commit — `feat(features): vol_of_vol layer (SpotV2Net edge-feature proxy)`

## Task 2: Edge-feature augmentation in `graph_data`

**Copilot context packet:**

```yaml
subtask_id: "gnn-05-2"
goal: "Add augment_edge_features(graphs, x_col_idx) producing (E,3) edge_attr [weight, vov_src, vov_dst], a GraphConfig.edge_features knob ('weight'|'volofvol'), and wiring in _run_one_horizon_graphs; tested."
file_scope:
  - workspace/plans/gnn/plan-05-attention-upgrades.md
  - src/volforecast/pipeline/graph_data.py
  - src/volforecast/pipeline/runner.py            # _run_one_horizon_graphs
  - src/volforecast/config.py
write_scope:
  - src/volforecast/pipeline/graph_data.py
  - src/volforecast/pipeline/runner.py
  - src/volforecast/config.py
  - src/tests/unit/test_graph_data.py
  - workspace/configs/_CANONICAL_EXAMPLE.yaml
acceptance_criteria:
  - "./vol test -k test_graph_data -> pass (new + old)"
  - "edge_features='volofvol' requires 'vov_d' in node_features at config parse -> ValueError otherwise"
  - "edge_attr shape (E,3); row = [w_ij, x[src, vov_idx], x[dst, vov_idx]]"
constraints: ["TDD failing-first", "Default 'weight' leaves graph dicts byte-identical (characterization)", "Zero-filled vov (missing node) is passed through, not NaN"]
context_summary: |
  Widens edge attributes so attention scores can condition on endpoint vol-of-vol. The vov
  values are already node features (Task 1's columns, included via graph.node_features); the
  augmentation lifts them onto edges: for each edge (i,j), attr = [weight, vov_i, vov_j].
  GNNVolModel already passes edge_attr through GATv2Conv(edge_dim=...); Task 3 makes edge_dim
  dynamic.
depends_on: ["gnn-05-1"]
```

Core implementation:

```python
def augment_edge_features(graphs: list[dict], vov_idx: int) -> list[dict]:
    """edge_attr (E,) -> (E,3): [weight, vov_src, vov_dst] from node feature column vov_idx."""
    out = []
    for g in graphs:
        ei = g["edge_index"]
        w = g["edge_attr"].float().reshape(-1)
        x = torch.from_numpy(g["x"])
        if ei.numel():
            attr = torch.stack([w, x[ei[0], vov_idx], x[ei[1], vov_idx]], dim=1)
        else:
            attr = torch.zeros(0, 3)
        out.append({**g, "edge_attr": attr})
    return out
```

Runner wiring in `_run_one_horizon_graphs`: after `build_graph_dataset`, `if graph_cfg.edge_features == "volofvol": graphs_all = augment_edge_features(graphs_all, node_cols.index("vov_d"))`. Config validation in `GraphConfig.__post_init__`. Commit — `feat(pipeline): vol-of-vol edge-feature augmentation`

## Task 3: `conv_type`, dynamic `edge_dim`, `spillover_matrix()`

**Copilot context packet:**

```yaml
subtask_id: "gnn-05-3"
goal: "Extend GNNVolModel with conv_type ('gatv2'|'transformer' via TransformerConv), edge_dim inferred from the first graph's edge_attr, and spillover_matrix(graphs) exporting the dst-normalized mean attention as an NxN DataFrame; characterization test proves defaults unchanged."
file_scope:
  - workspace/plans/gnn/plan-05-attention-upgrades.md
  - src/volforecast/models/gnn.py                  # the file being extended — read fully
  - src/tests/unit/test_gnn.py                     # existing tests must stay green
write_scope:
  - src/volforecast/models/gnn.py
  - src/tests/unit/test_gnn_attention.py
acceptance_criteria:
  - "./vol test -k 'test_gnn or test_gnn_attention' -> all pass"
  - "Characterization: fixed-seed fit+predict on the shared spillover fixture identical before/after (capture expected values in the test BEFORE refactoring, from the pre-change code)"
  - "conv_type='transformer' trains and predicts on directed (dy-style) graphs"
  - "spillover_matrix returns (N,N) DataFrame, rows/cols = symbols, rows sum to ~1 on connected nodes"
constraints:
  - "TDD: write the characterization test against CURRENT code first, commit it, then refactor"
  - "TransformerConv(root_weight=True) is the UniMP self-term; heads/concat wiring mirrors the GATv2 pair"
  - "edge_dim = edge_attr.shape[-1] if 2-D else 1; _GATModule takes it as a parameter (already does)"
  - "spillover_matrix requires symbols: pass tuple via fit(graphs) capture of g['x'].shape[0] + a symbols kwarg with default None -> integer labels"
context_summary: |
  Three surgical extensions to models/gnn.py. (1) conv_type: build conv1/conv2 from a
  {'gatv2': GATv2Conv, 'transformer': TransformerConv} map — TransformerConv is PyG's UniMP
  operator (GTN-VF's core). (2) edge_dim: currently hard-coded 1 and edge_attr unsqueezed to
  (E,1); accept (E,k) attrs from Task 2 without unsqueezing when already 2-D. (3)
  spillover_matrix: run extract_features-style forward with return_attention=True, scatter mean
  attention onto (dst, src) cells, normalize rows by in-degree — the learned analogue of the DY
  table. Docstring must carry the not-causal caveat verbatim from the plan.
depends_on: ["gnn-05-2"]
```

Key test cases (`test_gnn_attention.py`):

```python
def test_characterization_default_unchanged(spillover_graphs):
    """Pin current behavior: fixed-seed GATv2 predictions must not move."""
    m = GNNVolModel(input_dim=1, hidden_dim=8, n_heads=2, max_epochs=5,
                    device="cpu", seed=42).fit(spillover_graphs[:60])
    preds = m.predict(spillover_graphs[60:65])
    # EXPECTED captured from pre-change code by running this test body once before refactor:
    np.testing.assert_allclose(preds, EXPECTED_PRE_CHANGE, atol=1e-6)

def test_transformer_conv_type_runs(spillover_graphs): ...
def test_edge_attr_3dim_accepted(spillover_graphs_with_3d_edges): ...
def test_directed_graph_attention(dy_style_directed_graphs): ...
def test_spillover_matrix_shape_and_row_norm(spillover_graphs):
    m = GNNVolModel(...).fit(spillover_graphs)
    sm = m.spillover_matrix(spillover_graphs[-21:], symbols=["A","B","C","D"])
    assert sm.shape == (4, 4) and (sm.values.diagonal() == 0).all()
    np.testing.assert_allclose(sm.sum(axis=1), 1.0, atol=1e-6)
def test_unknown_conv_type_raises(): ...
```

`spillover_matrix` reference:

```python
def spillover_matrix(self, graphs, *, symbols=None) -> pd.DataFrame:
    """Mean layer-2 attention aggregated to an N x N 'who-influences-whom' table.

    CAVEAT (chapter §Attention): these are trained parameters that co-move with
    regimes — NOT identified causal spillovers; and interpretability output can
    reflect training-period idiosyncrasies (SpotV2Net's GNNExplainer lesson).
    """
    ...  # forward with return_attention=True over a mega-batch;
         # acc[dst, src] += mean-head attention; count[dst, src] += 1;
         # M = acc / count; zero diagonal; row-normalize by row sums (safe).
```

Commit — `feat(models): conv_type transformer, multi-dim edge attrs, spillover export`

## Task 4: The attention-hypothesis experiment

**Copilot context packet:**

```yaml
subtask_id: "gnn-05-4"
goal: "Create trial_083: gnnhar_1l (fixed weights, incumbent) vs gnn_gatv2 vs gnn_gatv2_edgefeat vs gnn_transformer, same graph, h=1/5/22; register with the explicit 'attention may lose' hypothesis."
file_scope:
  - workspace/plans/gnn/plan-05-attention-upgrades.md
  - workspace/configs/trial_082_gnnhar_vs_ghar_stid.yaml
  - workspace/research/trials.yaml
write_scope:
  - workspace/configs/trial_083_attention_upgrades.yaml
  - workspace/research/trials.yaml
acceptance_criteria: ["Config parses", "trial-083 registered NOT_STARTED with hypothesis + null-is-a-finding note"]
constraints: ["Do NOT run vol run", "graph block = trial_080 winner; node_features must include vov_d for the edgefeat arm"]
context_summary: |
  Hypothesis: input-dependent attention weights beat fixed GLASSO/DY weights on our universe
  (untested anywhere under QLIKE+DM). Four arms differ only in the message function M of the
  MPNN template. Baseline = gnnhar_1l from trial_082. Expect: attention ties or loses; the
  edge-feature arm is the most likely winner if any (SpotV2Net's 'features over topology').
depends_on: ["gnn-05-3"]
```

`trial_083_attention_upgrades.yaml` (abridged — same universe/dates/cv/tournament scaffold as trial_082, `n_gpus: 8`, `parallel_models: 1`):

```yaml
feature_layers: [har_core, asymmetry, vol_of_vol]
graph:
  method: glasso            # trial_080 winner
  window: 1000
  refit_every: 21
  node_features: [log_rv_d, log_rv_w, log_rv_m, signed_return_d, abs_ret_d,
                  log_rs_negative_d, log_jump_d, log_bpv_d, log_cont_d, vov_d]
tournament:
  models: [har, gnnhar_1l, gnn_gatv2, gnn_edgefeat, gnn_transformer]
  baseline: har
  parallel_models: 1
  model_configs:
    gnnhar_1l:      {name: gnnhar, params: {hidden_dim: 9, n_layers: 1, loss: qlike, n_seeds: 5}}
    gnn_gatv2:      {name: gnn, params: {hidden_dim: 32, n_heads: 4, loss: qlike, conv_type: gatv2}}
    gnn_edgefeat:
      name: gnn
      params: {hidden_dim: 32, n_heads: 4, loss: qlike, conv_type: gatv2}
      graph: {method: glasso, window: 1000, refit_every: 21, edge_features: volofvol,
              node_features: [log_rv_d, log_rv_w, log_rv_m, signed_return_d, abs_ret_d,
                              log_rs_negative_d, log_jump_d, log_bpv_d, log_cont_d, vov_d]}
    gnn_transformer: {name: gnn, params: {hidden_dim: 32, n_heads: 4, loss: qlike, conv_type: transformer}}
```

Interpretation protocol in the trial entry: DM of each attention arm vs `gnnhar_1l`; export `spillover_matrix` over the last test year into `workspace/tmp/` for the research journal; compare its top edges with the DY graph's (qualitative note only).

## 6. Orchestrator prompt

```
/execute Implement Plan 05 (attention upgrades) from workspace/plans/gnn/plan-05-attention-upgrades.md
Precondition: Plan 04 merged. Sequence: gnn-05-1 -> gnn-05-2 -> gnn-05-3 -> gnn-05-4.
CRITICAL for gnn-05-3: the characterization test is written and committed against the
CURRENT gnn.py BEFORE any modification (run it once to capture expected values).
TDD everywhere; ./vol only; return contracts. Integration: ./vol test-all, lint, typecheck.
Weekly-progress entry. Print trial_083 launch command; do NOT run. Do NOT start Plan 06.
```

## Acceptance gate → Plan 06

Tests green incl. characterization; `spillover_matrix` produces sane tables on synthetic data; trial_083 registered. Science outcome recorded either way — "attention does not beat fixed weights on our data under DM" is a thesis-grade internal finding.
