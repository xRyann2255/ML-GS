# Plan: Generic HAR-X Model — Config-Driven Feature Injection

**Status:** DESIGN complete, ready for /execute
**Owner:** vincry
**Baseline:** [src/volforecast/models/har_family.py](../../src/volforecast/models/har_family.py) (frozen `_FEATURES` per class)
**Motivation:** Every HAR-X variant today is a hard-coded class. Adding "HAR + feature X" for research probes requires editing Python and re-registering. Give the config layer the same expressive power via `model.params.extra_features`.
**Created:** 2026-07-28
**Workflow:** /plan → /execute

---

## 1. Scope

Ship a generic `harx` (Heterogeneous Autoregressive with eXogenous features) model — plus `ridge_harx` / `lasso_harx` / `elasticnet_harx` siblings — whose feature set is driven entirely by YAML. Any user-supplied column that lands in the training matrix can be appended to the HAR core with one line of config, no Python edits, no new registered model per feature combination.

### In scope

- New `HARXModel` class in [src/volforecast/models/har_family.py](../../src/volforecast/models/har_family.py) with `extra_features: list[str] | None = None` constructor kwarg.
- Auto-generated ridge / lasso / elasticnet variants via the existing `_register_regularized_variants()` factory.
- Feature-layer resolution: when a `harx` model is used, the runner must load the union of layers that supply the requested `extra_features` (not just `har_core`).
- TDD unit tests: constructor behavior, `_FEATURES` composition, `get_params()` round-trip, fit/predict on a synthetic panel, and missing-column error path.
- Integration test: end-to-end tournament run against a small config that stacks two extra features onto HAR core and produces the expected column list in the fitted `_feature_names`.
- Docs: enum update in [.github/instructions/yaml-config.instructions.md](../../.github/instructions/yaml-config.instructions.md#L73), one canonical example config, an entry in [workspace/docs/user-manual.md](../docs/user-manual.md) under model reference.

### Out of scope (deferred)

- Model training / QLIKE evaluation of any `harx` variant on real data. That belongs in `/experiment` after code lands.
- Feature interaction terms (e.g. `gex × iv_term_slope`). The generic HAR-X accepts columns that already exist in the matrix — building new interaction columns is a feature-layer concern.
- Per-horizon `extra_features` overrides via `horizon_overrides.<h>.model.params.extra_features`. The plumbing already exists via `Config.model_params_for_horizon(h)` — we only add a test that confirms it round-trips, no new code.
- Auto-derivation of `REQUIRED_LAYERS` from feature-name prefixes. Explicit `feature_layers` in the top-level config is the sanctioned mechanism; the model's `REQUIRED_LAYERS` stays permissive (`["har_core"]`) and the config author is responsible for listing needed layers.
- LSTM / XGBoost analogs. XGBoost already accepts arbitrary columns (`feature_layers` drives its input). HARX is the linear-model gap.

---

## 2. Architectural Decision: Instance-Level `_FEATURES`, Not Class-Level

**Decision:** `HARXModel.__init__` sets `self._FEATURES` on the instance from `extra_features`, shadowing the class attribute. All other model classes keep their class-level `_FEATURES`.

**Reasoning:**

| Consideration | Class-attribute-only (status quo) | Instance-level override (this plan) |
|---|---|---|
| Adding "HAR + feature X" | New subclass + `@register_model` + import wiring | One line in YAML |
| Runner instantiation | `model_cls()` — no args needed | `model_cls(extra_features=[...])` — already how the runner works: [runner.py#L158](../../src/volforecast/pipeline/runner.py#L158) `model_cls(**fold_params)` |
| `_select_features` code | Reads `self._FEATURES` (already resolves via `self`) | Same code path — no changes to [_base.py#L127](../../src/volforecast/models/_base.py#L127) |
| Regularized variants | Factory hard-codes `_FEATURES` list into the generated class | Factory needs a small tweak: for `harx` family, pass `extra_features` through `__init__` |
| `get_params()` round-trip | Returns `{alpha, l1_ratio}` | Must also return `extra_features` so the runner's cached-params re-fit gives an identical estimator |
| `REQUIRED_LAYERS` gating | Class-level, hard-coded per variant | Class-level `["har_core"]` on `HARXModel`; the config's top-level `feature_layers` drives loading (already supported: [_model_utils.py#L61](../../src/volforecast/evaluation/_model_utils.py#L61)) |

`_BaseOLS._select_features` at [_base.py#L125-L135](../../src/volforecast/models/_base.py#L125) already dereferences `self._FEATURES` — no fork of the base class needed. This keeps blast radius minimal.

---

## 3. Acceptance Criteria

**Code:**
- `harx`, `ridge_harx`, `lasso_harx`, `elasticnet_harx` all present in `MODEL_REGISTRY` after `ensure_registered()`.
- `HARXModel(extra_features=["log_atm_iv_0dte_d", "gex_zscore_d"])._FEATURES == ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_0dte_d", "gex_zscore_d"]`.
- `HARXModel(extra_features=None)._FEATURES == ["log_rv_d", "log_rv_w", "log_rv_m"]` (identical to `HARModel`).
- `HARXModel(extra_features=[...]).get_params() == {"extra_features": [...]}`; `RidgeHARXModel(extra_features=[...], alpha=0.5).get_params() == {"extra_features": [...], "alpha": 0.5}`.
- Instantiating with a column not present in the training matrix raises the same `ValueError` as any other HAR variant — no silent drop.
- No existing test regresses; new tests pass.
- `./vol lint` and `./vol typecheck` clean (run only at end per [copilot-instructions.md Rule 6](../../.github/copilot-instructions.md)).

**Tests (TDD — write failing first):**
- [src/tests/unit/models/test_harx.py](../../src/tests/unit/models/test_harx.py) covers:
  1. Empty / None `extra_features` behaves as plain HAR.
  2. Extra features are appended (order preserved).
  3. `fit` + `predict` on a synthetic 200-row DataFrame produces finite output.
  4. `get_params()` round-trips through `HARXModel(**model.get_params())`.
  5. Missing-column instantiation raises `ValueError` with the missing column in the message.
  6. Regularized variants (ridge/lasso/elasticnet) accept `extra_features` and their alpha kwarg simultaneously.
  7. Horizon-override plumbing: `Config` fixture with `horizon_overrides.5.model.params.extra_features` merges correctly through `model_params_for_horizon(5)`.

**Config + docs:**
- New canonical example [workspace/configs/example_harx.yaml](../configs/example_harx.yaml) — plain HAR-X with `extra_features: [log_atm_iv_0dte_d, dealer_gamma_zscore_d]`, single horizon, tiny date range. Not a trial config, purely illustrative.
- Enum row in [yaml-config.instructions.md#L73](../../.github/instructions/yaml-config.instructions.md#L73) extended: `harx`, `ridge_harx`, `lasso_harx`, `elasticnet_harx` (with a short prose note that `extra_features` is the required param).
- [workspace/docs/user-manual.md](../docs/user-manual.md) model-reference section gains a paragraph describing the generic HAR-X.

**Integration:**
- Small end-to-end tournament run using [example_harx.yaml](../configs/example_harx.yaml) (SPY only, 1-year window, h=1) completes without error and the persisted metrics parquet contains a row for `harx` with a finite QLIKE. No claim about *how good* the QLIKE is — only that the pipeline plumbing survives config-driven feature injection.

**NOT part of AC:**
- Any real experiment result. Trial-103 (GEX interactions) and any HAR-X-vs-champion tournament come after `/execute` via `/experiment`.

---

## 4. Dependency Graph

```
execute-1: test scaffold + failing tests  ──┐
                                            │
                    (depends on 1)          ▼
                                    execute-2: HARXModel impl + factory hook
                                            │
                                            ├────────────────────────────┐
                                            ▼                            ▼
                                execute-3: example config           execute-4: docs
                                    + integration test              (enum + user-manual)
                                            │                            │
                                            └──────────────┬─────────────┘
                                                           ▼
                                                execute-5: verify + memory update (inline)
```

**Parallelism:** execute-3 and execute-4 fan out from execute-2. execute-1 must complete first (failing tests define the contract). execute-5 is the leader's integration gate — no subagent.

---

## 5. Steps (with execution-mode tags)

### execute-1 — TDD scaffold (SUBAGENT)

```yaml
subtask_id: "execute-1"
goal: "Write failing unit tests in src/tests/unit/models/test_harx.py that pin the HARXModel contract per §3 Tests. Tests MUST fail (collection error or ValueError) because HARXModel does not yet exist."
file_scope:
  - src/volforecast/models/_base.py
  - src/volforecast/models/har_family.py
  - src/volforecast/registry.py
  - src/volforecast/config.py
  - src/tests/unit/models/test_har_family.py
  - src/tests/conftest.py
write_scope:
  - src/tests/unit/models/test_harx.py
acceptance_criteria:
  - "File exists, contains 7 test functions matching §3 Tests items 1-7"
  - "`./vol test src/tests/unit/models/test_harx.py -x -q` fails with ImportError or ValueError (harx not registered)"
  - "No changes to any file outside write_scope"
memory_refs:
  - memory/research/project-state.md
constraints:
  - "TDD strict: tests must fail on first run"
  - "Do not implement HARXModel or edit har_family.py"
  - "Reuse fixtures from src/tests/conftest.py where they exist; do not invent new global fixtures"
  - "Use ./vol test for all pytest invocations (never bare pytest)"
context_summary: |
  We are adding a generic HAR-X model whose feature list is driven by YAML
  `model.params.extra_features`. Every existing HAR-X variant hard-codes
  `_FEATURES` at class level. This step ONLY writes the tests that pin
  the new class's contract; the next step implements the class to make
  them pass. The base class `_BaseOLS._select_features` at
  src/volforecast/models/_base.py L125-L135 already reads `self._FEATURES`,
  so instance-level `_FEATURES` will work — no base-class changes needed.
depends_on: []
```

### execute-2 — HARXModel + regularized variants (SUBAGENT)

```yaml
subtask_id: "execute-2"
goal: "Implement HARXModel and hook it into _register_regularized_variants so ridge/lasso/elasticnet siblings auto-register. All 7 tests from execute-1 pass."
file_scope:
  - src/volforecast/models/har_family.py
  - src/volforecast/models/_base.py
  - src/volforecast/registry.py
  - src/tests/unit/models/test_harx.py
write_scope:
  - src/volforecast/models/har_family.py
acceptance_criteria:
  - "`./vol test src/tests/unit/models/test_harx.py -q` — all 7 tests pass"
  - "`./vol test src/tests/unit/models/ -q` — no existing test regresses"
  - "HARXModel class is registered via @register_model('harx'); ridge_harx/lasso_harx/elasticnet_harx appear in MODEL_REGISTRY"
  - "HARXModel.REQUIRED_LAYERS == ['har_core'] (permissive — config-level feature_layers drives loading)"
  - "HARXModel.__init__ signature: `(self, extra_features: list[str] | None = None, model=None)`"
  - "get_params() returns extra_features (list, not None); regularized variants also return alpha (+ l1_ratio for lasso/elasticnet)"
memory_refs: []
constraints:
  - "Do not modify _BaseOLS or _base.py — instance-level self._FEATURES is sufficient"
  - "Follow the existing _register_regularized_variants pattern at har_family.py L1648. The factory currently hard-codes features into the generated class; extend it so harx-family variants accept extra_features through __init__ and set self._FEATURES on the instance"
  - "Do NOT add horizon-specific harx_h1/h5/h22 classes — this is a single generic model"
  - "Preserve the existing _NEW_HYBRID_SPECS list; append harx to it or add a separate spec list — do not delete or reorder existing entries"
  - "Use ./vol lint at end to catch style violations — must be clean before returning"
context_summary: |
  execute-1 has produced failing tests. This step implements HARXModel:
  HAR core (log_rv_d/w/m) + any user-supplied columns. The regularized
  factory `_register_regularized_variants` at har_family.py L1648-L1699
  currently freezes `_FEATURES` at class-definition time. It needs to
  accept a "features come from constructor kwarg" mode for the harx family
  only. Existing `_ridge_init/_lasso_init/_enet_init` closures already
  accept **kwargs pattern — extend them to also accept and store
  extra_features, then set self._FEATURES on the instance after super()
  __init__. Runner path at pipeline/runner.py L158 calls
  `model_cls(**fold_params)`, so extra_features flows from YAML through
  Config.model_params_for_horizon into the constructor unchanged.
depends_on: ["execute-1"]
```

### execute-3 — Example config + integration test (SUBAGENT)

```yaml
subtask_id: "execute-3"
goal: "Create workspace/configs/example_harx.yaml and add an integration test that runs a tiny tournament end-to-end using the generic harx model."
file_scope:
  - workspace/configs/trial_063_xgboost_champion.yaml
  - workspace/configs/baseline_har.yaml
  - src/volforecast/config.py
  - src/volforecast/pipeline/runner.py
  - src/tests/integration/
write_scope:
  - workspace/configs/example_harx.yaml
  - src/tests/integration/test_harx_end_to_end.py
acceptance_criteria:
  - "example_harx.yaml parses via Config.from_yaml without error"
  - "Config uses `model.name: harx` and `model.params.extra_features: [log_atm_iv_0dte_d]` (or another column present in existing test fixtures)"
  - "Integration test runs a tournament on SPY only, 6-month window, h=1"
  - "Test asserts: metrics parquet contains a row for model=='harx', qlike is finite, len(model._feature_names) == 4"
  - "`./vol test src/tests/integration/test_harx_end_to_end.py -q` passes"
  - "Test runtime < 60 seconds (skip if it exceeds — use pytest.mark.slow)"
memory_refs:
  - workspace/docs/user-manual.md
constraints:
  - "Do not modify pipeline/runner.py — the integration test proves the runner already handles this"
  - "Use ./vol test (never bare pytest)"
  - "Config must be a MINIMAL illustrative example — no VRP, no VIX, no tournament economics toggles"
  - "If integration test cannot complete in <60s on the local fixtures, mark @pytest.mark.slow and document in the plan-followup"
context_summary: |
  execute-2 has landed HARXModel. This step proves the model works end-to-end
  through the actual tournament runner without any runner changes. The runner
  at pipeline/runner.py L158, L336, L587 already instantiates via
  model_cls(**fold_params). If extra_features flows through, the model
  self-configures its _FEATURES and fits normally. The example config also
  becomes the docs anchor: user-manual.md will link to it.
depends_on: ["execute-2"]
```

### execute-4 — Docs update (SUBAGENT)

```yaml
subtask_id: "execute-4"
goal: "Add harx family to the YAML config enum and document the generic HAR-X in user-manual.md."
file_scope:
  - .github/instructions/yaml-config.instructions.md
  - workspace/docs/user-manual.md
  - workspace/configs/example_harx.yaml
write_scope:
  - .github/instructions/yaml-config.instructions.md
  - workspace/docs/user-manual.md
acceptance_criteria:
  - "yaml-config.instructions.md L73 (HAR-IV enum row) extended with harx, ridge_harx, lasso_harx, elasticnet_harx and a one-line note pointing to `extra_features`"
  - "user-manual.md model-reference section gains ~10 lines describing HARXModel: purpose, params.extra_features contract, example YAML fragment"
  - "Both docs cross-link to workspace/configs/example_harx.yaml"
  - "No stylistic rewrite of surrounding docs — only additive edits"
memory_refs: []
constraints:
  - "Additive only — do not restructure surrounding sections"
  - "Follow the fileLinkification rules in copilot-instructions.md when adding links"
  - "Do NOT create new markdown files"
context_summary: |
  execute-2 and execute-3 have landed the model and example config.
  This step surfaces the new capability in the two docs the user will look
  at first: the YAML instructions file (which is loaded whenever any
  workspace/configs/** file is edited) and the user manual model reference.
depends_on: ["execute-2"]
```

### execute-5 — Integration verification + memory update (INLINE)

Leader-only. No subagent. Steps:

1. Run `./vol test src/tests/unit/models/test_harx.py src/tests/integration/test_harx_end_to_end.py -q` and confirm pass.
2. Run `./vol lint` and `./vol typecheck` — must be clean.
3. Read the diff of all files in the four subagents' `write_scope` and sanity-check nothing outside was touched.
4. Update [memory/research/project-state.md](../../memory/research/project-state.md) "Key Decisions Made" with a one-line entry: "Generic HAR-X model (`harx` + ridge/lasso/elasticnet siblings) landed — config-driven extra_features unlocks Layer-N-plus-HAR probes without new Python classes."
5. Append a dated entry to [workspace/research/weekly-progress.md](../research/weekly-progress.md) under the current week (Shipped bullet).
6. Kill any background terminals spawned during verification (EXIT GATE per [copilot-instructions.md Rule 4](../../.github/copilot-instructions.md)).

---

## 6. Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| `_register_regularized_variants` refactor breaks existing ridge/lasso/elasticnet HAR-X variants | Medium | execute-2 AC requires no regression in `src/tests/unit/models/`. If the factory refactor is invasive, isolate the harx branch: leave the existing closure-based specs untouched and add a separate `_register_harx_variants` that only handles the generic family. |
| Runner does not thread `extra_features` through the tuning cache | Low | `get_params()` returns `extra_features`; the runner's cached-params re-fit calls `model_cls(**get_params())`. Covered by execute-1 test 4 (round-trip). |
| `REQUIRED_LAYERS = ["har_core"]` causes the runner to skip loading the layer that supplies an `extra_feature` | Medium | Explicit AC in execute-3 integration test: the top-level `feature_layers` in `example_harx.yaml` must include the layer that owns the extra column. `resolve_model` at [_model_utils.py#L61](../../src/volforecast/evaluation/_model_utils.py#L61) already prefers top-level `feature_layers` over model `REQUIRED_LAYERS` — this is documented behavior. execute-4 docs will make the "you must list the layer" requirement explicit. |
| Column-name typo in YAML silently drops the feature | Low | `_BaseOLS._fit` raises `ValueError` when *none* of `_FEATURES` are present. If SOME are present but the typo'd column is missing, current behavior silently drops it. Add a stricter check in `HARXModel.fit` that errors if any `extra_features` column is missing from `X.columns` (documented in execute-2 AC — see test item 5). |
| Integration test flaky due to fixture data drift | Low | Use `SPY` + a hard-coded 6-month window that lives in existing test fixtures. If drift becomes an issue, add a small synthetic fixture to `src/tests/integration/fixtures/` in a follow-up. |

---

## 7. Verification Evidence Required (per Rule 7)

At execute-5 completion, the leader posts:

- `./vol test src/tests/unit/models/test_harx.py -q` full output (7 passed).
- `./vol test src/tests/integration/test_harx_end_to_end.py -q` full output (1 passed).
- `./vol lint` output (0 issues).
- `./vol typecheck` output (0 issues).
- `git diff --stat` showing only the write-scoped files changed.

No "done" claim without all five.

---

## 8. Post-Landing (out of this plan)

- `/experiment` trial-103: HAR-X with `extra_features: [dealer_gamma_zscore_d]` at h=22 — is the +68 bps GEX gain in [trial-098](../research/trials.yaml#L3434) linearly recoverable, or does XGBoost's nonlinearity carry the signal?
- `/experiment`: HAR-X sweep over the top-10 unranked columns from [final_optimal_feature_set.md](../research/final_optimal_feature_set.md) as a fast linear-family screen before committing tree-model compute.
- Per-horizon `extra_features` via `horizon_overrides.<h>.model.params.extra_features` — the plumbing exists; add a trial config that uses it if the initial sweep motivates horizon-specific gating.
