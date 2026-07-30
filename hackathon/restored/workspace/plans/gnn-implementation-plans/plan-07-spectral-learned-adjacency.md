# Plan 07 — Spectral GSP-HAR + Learned Adjacency

> **For the Copilot orchestrator:** execute with `/execute` (§6). TDD hard gate. Requires Plans 01–06 merged. Two independent frontier arms in one plan: the *spectral* route (GSP-HAR) and the *learned-adjacency* route (MTGNN-style), plus the graph-quality diagnostic both need.

**Goal:** (a) `gsp_har` — the lightweight spectral alternative (Chi, Gao & Wang 2024, arXiv 2410.22706; repo `MikeZChi/GSPHAR`): encode the directed DY matrix in a **magnetic Laplacian** (coupling strength in magnitude, lead–lag direction in complex phase), graph-Fourier-transform the RV cross-section, fit learnable spectral filters, merge with the HAR channel. (b) `gnn_learned` — learn the adjacency end-to-end (MTGNN graph-learning layer; EMGNN motivates the evolving upgrade but crypto-only evidence ⇒ static learned first, evolving recorded as future work). (c) `graph_signal_energy` — the "diagnose the graph before you model on it" tool: `E(x) = xᵀ L x` spikes in crises on informative spillover graphs and stays flat on Pearson graphs (GSP-HAR Figs. 1–2).

**Architecture:**
- **Magnetic Laplacian** (GSP-HAR eqs. 6–9): `L^{(q)} = I − (D_s^{−1/2} W_s D_s^{−1/2}) ⊙ exp(i 2π q (W − Wᵀ))` with `W_s = ½(W + Wᵀ)`, `D_s` its degree matrix; Hermitian PSD ⇒ real non-negative eigenvalues, complex eigenvectors `U`. `q ≥ 0` tunes how much direction matters (`q = 0` discards it).
- **`gsp_har` model:** per refit-block, eigendecompose `L^{(q)}` once. Graph channel: `g = Re(U diag(h_re + i·h_im) U^H X)` — a learnable complex spectral filter applied to the node-feature cross-section — then `ŷ = α + Xβ + gγ`. Trained by Adam under QLIKE (gnnhar loop conventions). Since eigenvectors change only at graph refits, cache `U` per unique snapshot.
- **`gnn_learned` model:** ignores input edges; learns `A = ReLU(tanh(a·(M₁M₂ᵀ − M₂M₁ᵀ)))` with `M₁ = tanh(a·E₁Θ₁)`, `M₂ = tanh(a·E₂Θ₂)` (MTGNN eqs.), row-wise **top-k** sparsification (straight-through: mask forward, dense backward is unnecessary — mask both, k default 5), then a GNNHAR-style one-hop body over the learned `A`. Exposes `learned_adjacency() -> pd.DataFrame` for inspection.
- **Diagnostic:** `graph_signal_energy(snapshot, x)` in `graphs/diagnostics.py`; `energy_series(schedule, panel)` per date.

**Tech stack:** numpy `eigh` on complex Hermitian (magnetic Laplacian), pure torch models. No new dependencies.

**Research grounding / calibration:** GSP-HAR's own SPX h=1 MSE gain over HAR is <3% (0.113→0.110), MCS only at lenient 25%, no QLIKE — expect near-tie under QLIKE; its lasting export is the energy diagnostic. Learned-static adjacency (MTGNN) lost to learned-evolving on crypto (EMGNN rel. MSFE 0.7809 vs 0.6527) but no predefined-vs-learned ablation exists on equities — ours will be the first on this universe; STID (Plan 04) already guards the "learned A ≈ node identity" deflation.

## Global constraints

As 00-overview §4.1. Plan-specific:
- Magnetic Laplacian gets a **formula gold test** (hand-computed 3-node directed example) registered in `FORMULAS.md`.
- `q = 0` must reduce `gsp_har`'s Laplacian to the standard symmetric-normalized Laplacian (unit test).
- `gnn_learned` with `top_k >= N-1` (dense) and `top_k = 0` (empty → nests QLIKE-HAR) both well-defined.

## File map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `src/volforecast/graphs/diagnostics.py` | `magnetic_laplacian`, `graph_signal_energy`, `energy_series` |
| Create | `src/volforecast/models/gsp_har.py` | `GSPHARVolModel` |
| Create | `src/volforecast/models/gnn_learned.py` | `GNNLearnedAdjModel` |
| Modify | `src/volforecast/registry.py` | imports |
| Create | `src/tests/unit/test_magnetic_laplacian.py`, `src/tests/unit/formulas/test_magnetic_laplacian_formulas.py` (+ gold JSON), `src/tests/unit/test_gsp_har.py`, `src/tests/unit/test_gnn_learned.py` | tests |
| Create | `workspace/configs/trial_085_spectral_learned.yaml` | experiment |

---

## Task 1: Magnetic Laplacian + graph signal energy (with gold values)

**Copilot context packet:**

```yaml
subtask_id: "gnn-07-1"
goal: "Add magnetic_laplacian(W, q) and graph_signal_energy/energy_series to graphs/diagnostics.py with a hand-computed 3-node gold-value formula test; verify Hermitian PSD and the q=0 reduction."
file_scope:
  - workspace/plans/gnn/plan-07-spectral-learned-adjacency.md   # Task 1: math + gold derivation
  - src/volforecast/graphs/diagnostics.py
  - src/tests/unit/formulas/FORMULAS.md
  - src/tests/unit/formulas/conftest.py
write_scope:
  - src/volforecast/graphs/diagnostics.py
  - src/tests/unit/test_magnetic_laplacian.py
  - src/tests/unit/formulas/test_magnetic_laplacian_formulas.py
  - src/tests/unit/formulas/gold_values/magnetic_laplacian_3node.json
  - src/tests/unit/formulas/FORMULAS.md
acceptance_criteria:
  - "./vol test -k magnetic -> all pass"
  - "L is Hermitian (L == L^H) and PSD (min eigenvalue >= -1e-10) for random directed W"
  - "q=0 equals I - D^-1/2 W_s D^-1/2 exactly"
  - "graph_signal_energy(snapshot, x) == x^T L x (real part) for real x"
constraints: ["TDD failing-first", "numpy only", "Formula test registered in FORMULAS.md: Chi, Gao & Wang (2024) eqs. 6-9; Shubin (1994) magnetic Laplacian"]
context_summary: |
  L^(q) = I - (D_s^-1/2 W_s D_s^-1/2) elementwise* exp(i 2 pi q (W - W^T)), W_s = (W+W^T)/2.
  Gold example: 3 nodes, single directed edge W[0,1] = 1 (else 0), q = 0.25:
  W_s = [[0,.5,0],[.5,0,0],[0,0,0]]; D_s = diag(.5,.5,0); normalized = [[0,1,0],[1,0,0],[0,0,0]];
  phase Theta = 2*pi*0.25*(W - W^T) -> Theta[0,1] = pi/2, Theta[1,0] = -pi/2;
  L[0,1] = -(1)*exp(i pi/2) = -i; L[1,0] = +i... careful: -(1)*exp(-i pi/2) = +i? exp(-i pi/2) = -i,
  so L[1,0] = -( -i ) = ... derive precisely in the JSON: L = I - H where H[0,1] = 1*e^{i pi/2} = i,
  H[1,0] = 1*e^{-i pi/2} = -i; hence L = [[1, -i, 0], [i, 1, 0], [0, 0, 1]] with eigenvalues {0, 2, 1}.
  Record this derivation in the gold JSON. graph_signal_energy: for snapshot -> dense W -> L^(0),
  E(x) = Re(x^H L x).
depends_on: []
```

Gold JSON expected values: `L = [[1,0,0],[0,1,0],[0,0,1]] - [[0,i,0],[-i,0,0],[0,0,0]]` ⇒ `L = [[1,-i,0],[i,1,0],[0,0,1]]`, eigenvalues `[0.0, 1.0, 2.0]`; for `x = [1, 1, 0]`: `E = Re(x^H L x) = Re(1 - i + i + 1) = 2.0`.

Implementation sketch:

```python
def magnetic_laplacian(w: np.ndarray, q: float = 0.25) -> np.ndarray:
    ws = 0.5 * (w + w.T)
    d = ws.sum(1)
    inv_sqrt = np.where(d > 0, 1.0 / np.sqrt(np.where(d > 0, d, 1.0)), 0.0)
    norm = inv_sqrt[:, None] * ws * inv_sqrt[None, :]
    phase = np.exp(1j * 2.0 * np.pi * q * (w - w.T))
    lap = np.eye(w.shape[0], dtype=complex) - norm * phase
    return lap


def graph_signal_energy(snapshot: GraphSnapshot, x: np.ndarray, q: float = 0.0) -> float:
    lap = magnetic_laplacian(snapshot.dense_adjacency(), q)
    return float(np.real(np.conjugate(x) @ lap @ x))


def energy_series(schedule: dict, panel: pd.DataFrame, q: float = 0.0) -> pd.Series:
    """Per-date roughness of the cross-section over its PIT graph. Crisis spikes = good graph."""
    ...
```

Commit — `feat(graphs): magnetic Laplacian + graph signal energy with gold-value test`

## Task 2: `GSPHARVolModel`

**Copilot context packet:**

```yaml
subtask_id: "gnn-07-2"
goal: "Implement GSPHARVolModel: cached eigendecomposition of the magnetic Laplacian per graph refit, learnable complex spectral filter on the graph channel, HAR channel + per-asset intercept, QLIKE-trained; registered as 'gsp_har' with tests."
file_scope:
  - workspace/plans/gnn/plan-07-spectral-learned-adjacency.md   # Task 2 section
  - src/volforecast/graphs/diagnostics.py                       # magnetic_laplacian (Task 1)
  - src/volforecast/models/gnnhar.py                            # fit-loop conventions
write_scope:
  - src/volforecast/models/gsp_har.py
  - src/volforecast/registry.py
  - src/tests/unit/test_gsp_har.py
acceptance_criteria:
  - "./vol test -k test_gsp_har -> all pass"
  - "q param plumbed: q=0 model trains; q=0.25 differs on directed graphs, identical on symmetric ones"
  - "Eigendecomposition computed once per unique snapshot (spy/counter test), not per date"
  - "Empty graph: spectral channel contributes 0 -> nests QLIKE-HAR (gnnhar-style nesting test)"
constraints: ["TDD failing-first", "np.linalg.eigh on the Hermitian L (complex); U/eigvals stored as torch complex64 buffers per refit block", "Filter parameters: h_re, h_im in R^N (one coefficient pair per graph frequency)", "Model contract identical to gnnhar (fit(graphs)/predict/save/load/get_params/summary)"]
context_summary: |
  GSP-HAR pipeline (Chi et al. 2024): GFT the cross-section (x_hat = U^H x per feature column),
  scale each frequency by a learnable complex coefficient, inverse-transform, take the real part
  -> graph channel g; y = alpha + X beta + g gamma. Snapshots repeat between refits (Plan-01
  schedule freezes them) — key the eigendecomposition cache on id(snapshot)-equivalent, i.e.
  the (edge_index bytes, edge_attr bytes) hash carried through the graph dict; simplest: the
  runner already reuses graph dicts between refits ONLY via the schedule, so cache on the
  id() of edge_index tensor object. For directed handling: build dense W from the dict, L via
  magnetic_laplacian(W, q). Empty graph -> L = I -> U = I, filter on identity basis: initialize
  h_re = 0 so the channel starts at zero and the nesting test passes at init;
  gamma initialized 0 as well.
depends_on: ["gnn-07-1"]
```

Module core:

```python
class _GSPHARModule(nn.Module):
    def __init__(self, n_nodes: int, input_dim: int) -> None:
        super().__init__()
        self.h_re = nn.Parameter(torch.zeros(n_nodes))
        self.h_im = nn.Parameter(torch.zeros(n_nodes))
        self.alpha = nn.Parameter(torch.zeros(n_nodes))
        self.beta = nn.Linear(input_dim, 1, bias=False)
        self.gamma = nn.Linear(input_dim, 1, bias=False)

    def forward(self, x, u):                       # x: (T,N,F) real; u: (T,N,N) complex
        xc = x.to(torch.complex64)
        x_hat = torch.einsum("tij,tjf->tif", u.conj().transpose(-2, -1), xc)
        filt = (self.h_re + 1j * self.h_im)[None, :, None]
        g = torch.einsum("tij,tjf->tif", u, x_hat * filt).real
        return self.alpha[None, :] + self.beta(x).squeeze(-1) + self.gamma(g).squeeze(-1)
```

Tests: nesting-at-init (`gamma`,`h` zero → predictions = HAR channel), planted low-frequency structure recovered better with the true graph than with identity, eigh-cache counter, save/load, seed determinism, `q` behavior. Commit — `feat(models): GSP-HAR magnetic-Laplacian spectral model`

## Task 3: `GNNLearnedAdjModel`

**Copilot context packet:**

```yaml
subtask_id: "gnn-07-3"
goal: "Implement GNNLearnedAdjModel: MTGNN-style learned adjacency (node embeddings E1/E2, directed anti-symmetric score, row top-k) feeding a GNNHAR-style one-hop body; input edges ignored; registered as 'gnn_learned'; learned_adjacency() inspection method; tests."
file_scope:
  - workspace/plans/gnn/plan-07-spectral-learned-adjacency.md   # Task 3 section
  - src/volforecast/models/gnnhar.py                             # body + fit loop to reuse
write_scope:
  - src/volforecast/models/gnn_learned.py
  - src/volforecast/registry.py
  - src/tests/unit/test_gnn_learned.py
acceptance_criteria:
  - "./vol test -k test_gnn_learned -> all pass"
  - "Graph-invariance to INPUT edges (same preds with edges stripped) — the adjacency is learned"
  - "On planted-spillover data, the learned A puts its largest off-diagonal mass on the true edges (top-k overlap >= 50%)"
  - "top_k=0 -> zero adjacency -> nests QLIKE-HAR"
constraints: ["TDD failing-first", "MTGNN graph-learning: M1=tanh(a*E1@Th1), M2=tanh(a*E2@Th2), A=relu(tanh(a*(M1@M2.T - M2@M1.T))), row top-k mask, row-normalize", "embed_dim default 8, top_k default 5, a (saturation) default 3.0", "learned_adjacency(symbols=None) -> DataFrame after fit"]
context_summary: |
  The learned-adjacency arm: is estimation (GLASSO/DY) beatable by end-to-end learning at
  N=21-34? MTGNN's layer learns a directed A from two node-embedding matrices; the
  anti-symmetric difference biases toward uni-directional edges. Body = one no-self-loop hop
  (reuse _GNNHARModule with W supplied as the learned A broadcast over dates, row-normalized).
  STID (Plan 04) is the standing deflation control for this model.
depends_on: []
```

Graph-learning layer:

```python
class _AdaptiveAdjacency(nn.Module):
    def __init__(self, n_nodes: int, embed_dim: int = 8, top_k: int = 5, alpha: float = 3.0):
        super().__init__()
        self.e1 = nn.Parameter(torch.randn(n_nodes, embed_dim) * 0.1)
        self.e2 = nn.Parameter(torch.randn(n_nodes, embed_dim) * 0.1)
        self.th1 = nn.Linear(embed_dim, embed_dim, bias=False)
        self.th2 = nn.Linear(embed_dim, embed_dim, bias=False)
        self.top_k, self.alpha = top_k, alpha

    def forward(self) -> torch.Tensor:
        m1 = torch.tanh(self.alpha * self.th1(self.e1))
        m2 = torch.tanh(self.alpha * self.th2(self.e2))
        a = torch.relu(torch.tanh(self.alpha * (m1 @ m2.T - m2 @ m1.T)))
        a = a.fill_diagonal_(0.0)
        if self.top_k < a.shape[0] - 1:
            if self.top_k <= 0:
                return torch.zeros_like(a)
            thresh = a.topk(self.top_k, dim=1).values[:, -1:]
            a = a * (a >= thresh)
        deg = a.sum(1, keepdim=True).clamp(min=1e-12)
        return a / deg
```

Commit — `feat(models): learned-adjacency GNN (MTGNN graph-learning layer)`

## Task 4: Experiment + energy diagnostic report

**Copilot context packet:**

```yaml
subtask_id: "gnn-07-4"
goal: "Create trial_085 (gsp_har + gnn_learned vs gnnhar_1l vs har, h=1/5/22, QLIKE) and register it; hypothesis includes the energy-diagnostic protocol (DY energy spikes in crises, corr energy doesn't)."
file_scope:
  - workspace/plans/gnn/plan-07-spectral-learned-adjacency.md
  - workspace/configs/trial_084_dcrnn_har.yaml
  - workspace/research/trials.yaml
write_scope:
  - workspace/configs/trial_085_spectral_learned.yaml
  - workspace/research/trials.yaml
acceptance_criteria: ["Config parses", "trial-085 registered with hypothesis + energy protocol"]
constraints: ["Do NOT run vol run", "gsp_har arm graph override: dy directed (q=0.25); gnn_learned arm graph: identity (edges ignored anyway — cheapest schedule)"]
context_summary: |
  Two frontier arms vs the Plan-04 incumbent. Priors: gsp_har near-tie (its SPX MSE gain was
  <3% and QLIKE-unverified); gnn_learned unknown on equities (first predefined-vs-learned
  ablation on this universe). Interpretation step also runs energy_series over the dy and corr
  schedules for 2020-02..2020-06 and appends the comparison to the research journal — the
  graph-quality result stands independently of model performance.
depends_on: ["gnn-07-2", "gnn-07-3"]
```

Arms (scaffold as trial_084): `models: [har, gnnhar_1l, gsp_har, gnn_learned]`, model_configs with `gsp_har: {params: {q: 0.25, loss: qlike}, graph: {method: dy, input: log_rv, window: 252, refit_every: 21, params: {var_lags: 4, fevd_horizon: 10, threshold: 0.05}}}` and `gnn_learned: {params: {embed_dim: 8, top_k: 5, hidden_dim: 9, loss: qlike}, graph: {method: identity}}`. Commit — `chore(config): trial_085 spectral + learned-adjacency arms`

## 6. Orchestrator prompt

```
/execute Implement Plan 07 (GSP-HAR + learned adjacency) from workspace/plans/gnn/plan-07-spectral-learned-adjacency.md
Precondition: Plan 06 merged. Waves: gnn-07-1 first; then gnn-07-2 and gnn-07-3 in parallel
(max 2 subagents); then gnn-07-4.
TDD red->green evidence; ./vol only; return contracts. Integration: ./vol test-all, lint,
typecheck; weekly-progress entry. Print trial_085 launch command; do NOT run.
Do NOT start Plan 08 (it may already be running in a parallel session — check trials.yaml notes).
```

## Acceptance gate → Plans 08/09

Formula gold tests green (magnetic Laplacian); both models registered and nesting/deflation-tested; trial_085 registered. The roster is now complete: `ghar, gnnhar, stid, gnn(+transformer/edgefeat), dcrnn_har, gsp_har, gnn_learned` — seven graph models through one harness.
