# Plan 09 — Hybrid Arms (Blend vs Stack) + Regime Fusion

> **For the Copilot orchestrator:** execute with `/execute` (§7). TDD hard gate. Requires Plans 02, 04 merged (05–08 helpful, not required). Two evidence-ranked programs in one plan, executed in the order the literature demands: **blend before stack, regime features before regime graphs** ("inverting that order is how projects burn a summer" — chapter §Regime Frontier).

**Goal:**
(A) **Hybrids** — settle the repo's standing question: does feeding GNN *node embeddings* into the tree champion beat feeding just the GNN's *scalar forecast*? Prior (standing verdict since 2026-05): arm A (blending) ≈ arm B (stacking) at far lower complexity; no finance paper shows otherwise (Choi–Kim is the negative exemplar; BGNN is rigorous but non-finance and reverse-direction).
(B) **Regime fusion** — the exemplar-backed first build: **filtered** Markov-switching regime probability as a feature (Fang & Ślepaczuk 2026: −5.1% QLIKE on HARQ, DM-significant, broad-based not crisis-only), then the incumbent-free frontier: regime-blended graphs (prior from Brief B: a monthly re-estimated single graph "wins or ties" — this arm is expected to tie, and that's a finding).

**Architecture:**
- `extract_features(..., outputs=["embedding"])` on `gnn`/`gnnhar` → final-layer node embeddings `(total_nodes, D)`; the feature-stack path fans them into columns `gnn_emb_00..gnn_emb_{D-1}`.
- `features/regime.py::RegimeLayer` (`@register_feature_layer("regime")`): two-state Markov-switching model on lagged daily log-RV, **strictly point-in-time**: parameters re-estimated monthly on the expanding window ending at the refit date, then **filtered** probabilities for post-refit dates computed by running the filter forward **with frozen parameters** (`statsmodels` `MarkovRegression(new_endog).filter(fitted_params)`). Columns: `regime_prob_d` (P[high-vol state], lagged), `regime_prob_w`.
- `regime_blend` graph builder (`@register_graph("regime_blend")`): estimate `A_calm`/`A_stress` on the window's calm/stress dates (classified by trailing 22-day cross-sectional mean RV above/below its within-window quantile `q`), emit the convex blend by the window-end state. Observable-state classification — no fitted detector inside the builder, fully PIT.

**Tech stack:** statsmodels `MarkovRegression` (already a core dep; use `switching_variance=True`). No new dependencies. (`jump-models` noted as a future detector upgrade — Shu, Yu & Mulvey 2024 — but not added: no new deps without need.)

**Leakage discipline (the two published traps, both tested):**
1. **Filtered, never smoothed** — smoothed probabilities use the full sample (Fang & Ślepaczuk use filtered "because they depend only on contemporaneously available information", §4.1.4).
2. **Frozen-parameter filtering** — filtered probs from a model *fit on the whole window* still leak parameter information to early dates; our refit-then-freeze-then-filter protocol matches the GNNHAR graph template. Unit test: probability at date t is invariant to perturbing data after the *next* refit date.

## File map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `src/volforecast/models/gnn.py`, `src/volforecast/models/gnnhar.py` | `embedding` output in `extract_features` |
| Modify | `src/volforecast/pipeline/runner.py` | multi-dim feature-stack columns (`gnn_emb_*`) in `_make_gnn_feature_stack_fn` |
| Create | `src/volforecast/features/regime.py` | `RegimeLayer` |
| Create | `src/volforecast/graphs/regime_blend.py` | `RegimeBlendGraphBuilder` |
| Modify | `src/volforecast/registry.py` | imports |
| Create | tests: `test_gnn_embeddings.py`, `test_regime_layer.py`, `test_regime_blend_graph.py` | |
| Create | configs: `trial_086_blend_vs_stack.yaml`, `trial_087_regime_feature.yaml`, `trial_088_regime_graphs.yaml` | |

---

## Task 1: Node embeddings through the feature stack

**Copilot context packet:**

```yaml
subtask_id: "gnn-09-1"
goal: "Add 'embedding' to extract_features on gnn (post-conv2 hidden state, mean over heads) and gnnhar (final H^L, mean over seed members), and make _make_gnn_feature_stack_fn expand multi-dim outputs into gnn_emb_NN columns; tested."
file_scope:
  - workspace/plans/gnn/plan-09-hybrids-regime-fusion.md
  - src/volforecast/models/gnn.py                        # extract_features (597-683)
  - src/volforecast/models/gnnhar.py
  - src/volforecast/pipeline/runner.py                   # _make_gnn_feature_stack_fn (~1914)
write_scope:
  - src/volforecast/models/gnn.py
  - src/volforecast/models/gnnhar.py
  - src/volforecast/pipeline/runner.py
  - src/tests/unit/test_gnn_embeddings.py
acceptance_criteria:
  - "./vol test -k test_gnn_embeddings -> pass"
  - "extract_features(graphs, outputs=['embedding']) returns {'embedding': (total_nodes, D)} float32"
  - "Feature-stack fan-out: a (T*N, 8) embedding becomes 8 columns gnn_emb_00..gnn_emb_07 aligned to the (date,symbol) rows; existing scalar outputs unchanged (characterization)"
  - "Valid-outputs error message lists 'embedding'"
constraints: ["TDD failing-first", "gnn: embedding = hidden after conv2+ELU (before the MLP head); gnnhar: H^L averaged over seed modules", "embed dim comes from the model (hidden_dim), NOT config — feature_stack.outputs stays a list of names"]
context_summary: |
  Arm B (stacking) needs per-node representations in the tree model's design matrix. gnn.py's
  extract_features already returns dict[str, np.ndarray] with (total_nodes,) arrays; extend the
  contract to allow (total_nodes, D). _make_gnn_feature_stack_fn currently maps each output name
  to one column named gnn_{output}; give 2-D outputs a zero-padded per-dim suffix. 8/16/32-d
  arms are produced by setting model hidden_dim per arm in the config, not by slicing.
depends_on: []
```

Commit — `feat(models): node-embedding extraction through the GNN feature stack`

## Task 2: Blend-vs-stack experiment

**Copilot context packet:**

```yaml
subtask_id: "gnn-09-2"
goal: "Create trial_086 blend-vs-stack: xgboost champion baseline vs +gnn_prediction (arm A) vs +embeddings at D=8/16/32 (arm B sub-arms), as separate configs sharing seeds/CV; register with the standing-verdict hypothesis."
file_scope:
  - workspace/plans/gnn/plan-09-hybrids-regime-fusion.md
  - workspace/configs/trial_063_xgboost_champion.yaml     # the champion scaffold
  - workspace/configs/trial_068_gnn_standalone.yaml       # feature_stack precedent
  - workspace/research/trials.yaml
write_scope:
  - workspace/configs/trial_086a_blend_scalar.yaml
  - workspace/configs/trial_086b_stack_emb8.yaml
  - workspace/configs/trial_086c_stack_emb32.yaml
  - workspace/research/trials.yaml
acceptance_criteria: ["All three parse", "Identical universe/dates/cv/seed across arms (diff check in the report)", "trials.yaml entries with the decision rule: stacking must beat blending with DM p<0.05 to displace it"]
constraints: ["Do NOT run vol run", "Arm A: feature_stack {source_model: gnn, outputs: [prediction], model_params: trial_068 values}; Arm B adds embedding + hidden_dim 8/32", "Full champion feature_layers (iv_surface, har_core, asymmetry, noise_robust, options, calendar, tree_expansion) — the hybrid rides the best tabular stack"]
context_summary: |
  The repo's central hybrid question. Purged expanding CV is already the harness default.
  Evaluation protocol in the trial entry: per-horizon QLIKE of B-arms vs A-arm with panel-DM;
  prior is A == B (Choi-Kim negative exemplar; blending verdict stands since 2026-05-12).
  Also record tree feature-importance share of gnn_* columns (explainability.enabled: true,
  treeshap) so 'embeddings are used but don't help' is distinguishable from 'ignored'.
depends_on: ["gnn-09-1"]
```

Commit — `chore(config): trial_086 blend-vs-stack arms`

## Task 3: `RegimeLayer` — filtered MS probability, PIT-frozen filtering

**Copilot context packet:**

```yaml
subtask_id: "gnn-09-3"
goal: "Implement features/regime.py RegimeLayer: two-state MarkovRegression(switching_variance=True) on lagged log-RV, monthly expanding refits with FROZEN-parameter forward filtering, emitting regime_prob_d/regime_prob_w; leakage tests are the core deliverable."
file_scope:
  - workspace/plans/gnn/plan-09-hybrids-regime-fusion.md   # Task 3: the PIT recipe
  - src/volforecast/features/noise_robust.py                # layer shape
  - src/volforecast/features/transforms.py
write_scope:
  - src/volforecast/features/regime.py
  - src/volforecast/registry.py
  - src/tests/unit/test_regime_layer.py
acceptance_criteria:
  - "./vol test -k test_regime_layer -> pass"
  - "PIT test 1 (filtered not smoothed): prob at t invariant to perturbing rv at t+1..refit boundary"
  - "PIT test 2 (frozen params): prob at t (t after refit R) invariant to perturbing data after the NEXT refit R+21"
  - "State identification: the high-vol state is the one with larger variance (label-switching guard); prob in [0,1]; regime_prob_d lagged by 1 day"
  - "Convergence failure on a window -> previous month's params reused with a logged warning (never NaN columns)"
constraints:
  - "TDD failing-first"
  - "Refit protocol: at refit date R, fit MarkovRegression(endog = dlog_rv[:R], k_regimes=2, switching_variance=True); for dates in (R, R+refit_every], probs = MarkovRegression(endog[:t]).filter(params_R).filtered_marginal_probabilities[-1, high_state]"
  - "Use .filter(params) — NEVER .smoothed_marginal_probabilities (repo detector rule from Brief B)"
  - "endog = np.log(rv).diff() lagged one day before any use; params: refit_every=21, min_history=252"
  - "Mark the full-history test slow if >2s; keep a fast 300-day variant in the default suite"
context_summary: |
  Fang & Slepaczuk (2026): filtered two-state MS probability injected as one extra regressor
  cut HARQ QLIKE 5.1% (DM-significant, broad-based). Their leakage discipline is the template:
  filtered probabilities only. We add the second discipline (frozen-params forward filtering)
  because in-window filtered probs still embed parameters estimated on later dates. statsmodels
  supports this: fit once, then construct a new model on the extended endog and call
  .filter(fitted_params) — no re-estimation. High-state = argmax of fitted variances.
depends_on: []
```

Core recipe (reference):

```python
@register_feature_layer("regime")
class RegimeLayer:
    """Filtered 2-state MS probability of the high-volatility state (PIT-frozen)."""

    def __init__(self, refit_every: int = 21, min_history: int = 252) -> None: ...

    def compute(self, daily_data: pd.DataFrame, *, context=None) -> pd.DataFrame:
        from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

        endog = np.log(daily_data["rv"].clip(lower=1e-20)).diff().shift(1).dropna()
        probs = pd.Series(np.nan, index=daily_data.index)
        params, high = None, None
        for k in range(self.min_history, len(endog), self.refit_every):
            window = endog.iloc[:k]
            try:
                res = MarkovRegression(window.values, k_regimes=2,
                                       switching_variance=True).fit(disp=False)
                params = res.params
                high = int(np.argmax([res.params[f"sigma2[{s}]"] for s in range(2)])) \
                    if hasattr(res.params, "__getitem__") else int(np.argmax(res.params[-2:]))
            except Exception:
                if params is None:
                    continue  # not yet estimable; leave NaN
            block_end = min(k + self.refit_every, len(endog))
            ext = MarkovRegression(endog.values[:block_end], k_regimes=2,
                                   switching_variance=True)
            filt = ext.filter(params).filtered_marginal_probabilities[:, high]
            probs.loc[endog.index[k:block_end]] = filt[k:block_end]
        return pd.DataFrame({"regime_prob_d": probs,
                             "regime_prob_w": probs.rolling(5).mean()},
                            index=daily_data.index)
```

Commit — `feat(features): filtered Markov-switching regime probability (PIT-frozen)`

## Task 4: `regime_blend` graph builder

**Copilot context packet:**

```yaml
subtask_id: "gnn-09-4"
goal: "Implement RegimeBlendGraphBuilder ('regime_blend'): split the estimation window into calm/stress dates by trailing cross-sectional RV vs its within-window quantile, build a base graph on each subset, emit the convex blend weighted by the window-end state; tests incl. PIT."
file_scope:
  - workspace/plans/gnn/plan-09-hybrids-regime-fusion.md
  - src/volforecast/graphs/base.py
  - src/volforecast/graphs/correlation.py
  - src/volforecast/graphs/glasso.py
  - src/volforecast/graphs/factor_residual.py            # composition pattern (base builder delegation)
write_scope:
  - src/volforecast/graphs/regime_blend.py
  - src/volforecast/registry.py
  - src/tests/unit/graphs/test_regime_blend_graph.py
acceptance_criteria:
  - "./vol test -k test_regime_blend_graph -> pass"
  - "On a window whose last day is stress (top-quartile trailing dispersion), blended weights == w*A_stress + (1-w)*A_calm with w = state indicator smoothed by params.blend (default hard 0/1)"
  - "Falls back to the plain base graph when either regime subset has < min_rows dates"
constraints: ["TDD failing-first", "Observable-state classification only (trailing 22d mean of row-wise squared returns) — no fitted detector inside the builder", "params: {base: corr|glasso, quantile: 0.75, blend: hard|soft, min_rows: 60, **base_params}", "Union of edge sets; weights blended; method='regime_blend'"]
context_summary: |
  Pattern 3 of the regime-fusion program — deliberately last, expected to tie a single monthly
  graph (Brief B prior; Cho & Lee's Hurst-triggered swap LOST to periodic retraining in both
  crises). Design avoids their trap: no latent-state trigger, just an observable trailing
  dispersion split within the PIT window, so the arm isolates 'does regime-conditioning the
  ADJACENCY help' from detector quality.
depends_on: []
```

Commit — `feat(graphs): regime-blended adjacency builder`

## Task 5: Regime experiments

**Copilot context packet:**

```yaml
subtask_id: "gnn-09-5"
goal: "Create trial_087 (regime feature: har_iv +/- regime layer; gnnhar +/- regime_prob_d as node feature) and trial_088 (single glasso vs regime_blend graphs under gnnhar), register both with evidence-ranked hypotheses."
file_scope:
  - workspace/plans/gnn/plan-09-hybrids-regime-fusion.md
  - workspace/configs/trial_082_gnnhar_vs_ghar_stid.yaml
  - workspace/research/trials.yaml
write_scope:
  - workspace/configs/trial_087_regime_feature.yaml
  - workspace/configs/trial_088_regime_graphs.yaml
  - workspace/research/trials.yaml
acceptance_criteria: ["Both parse", "trial-087 hypothesis quotes the Fang & Slepaczuk prior (-5.1% QLIKE on CSI300; expect smaller on SPX/US panel); trial-088 hypothesis states the tie prior", "Both specify the regime-conditional QLIKE breakdown (median-split + top-25%) as the interpretation protocol"]
constraints: ["Do NOT run vol run", "trial_087 arms: har_iv | har_iv_regime (har_iv + feature_layers +[regime]) | gnnhar_1l | gnnhar_regime (node_features + [regime_prob_d]) — regime enters ONCE per arm", "trial_088: gnnhar with graph glasso/1000/21 vs graph {method: regime_blend, params: {base: glasso, quantile: 0.75}}"]
context_summary: |
  The evidence-ranked regime program: (1) feature injection first — the only pattern with a
  DM-significant exemplar; (2) regime graphs last — no credible incumbent, tie expected.
  Both trials' interpretation includes the regime-conditional breakdown (does the gain
  concentrate in turbulence or is it broad-based? Fang & Slepaczuk found broad-based).
depends_on: ["gnn-09-3", "gnn-09-4"]
```

Commit — `chore(config): trial_087 regime feature + trial_088 regime graphs`

## 7. Orchestrator prompt

```
/execute Implement Plan 09 (hybrids + regime fusion) from workspace/plans/gnn/plan-09-hybrids-regime-fusion.md
Precondition: Plans 02 and 04 merged.
Waves: (gnn-09-1, gnn-09-3, gnn-09-4 in parallel, max 2 at a time) -> gnn-09-2 -> gnn-09-5.
The RegimeLayer leakage tests (gnn-09-3) are the plan's core deliverable — a subagent
returning without both PIT tests green is FAILED, not partial.
TDD; ./vol only; return contracts. Integration: ./vol test-all, lint, typecheck.
Weekly-progress entry. Print all launch commands; do NOT run. Do NOT start Plan 10.
```

## Acceptance gate → Plan 10

Embeddings flow through the stack; RegimeLayer passes both PIT tests; regime_blend builder registered; trials 086–088 registered. The full experiment queue for the grand tournament now exists: 079–088.
