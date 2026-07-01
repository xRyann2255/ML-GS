"""Experiment configuration dataclasses with YAML serialization.

For universe/symbol/field constants, see volforecast.constants.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def _parse_gsvivs_sizings(raw: Any) -> tuple[Any, ...] | None:
    """Parse the ``gsvivs_sizings`` YAML node into a tuple of GsvivsSizingSpec.

    ``None`` (key absent) is preserved so the runtime falls back to the
    project default 3-mode list. An empty list is honored as "no sizing
    variants" → empty tuple. The import is deferred to avoid a circular
    dependency between :mod:`volforecast.config` and
    :mod:`volforecast.evaluation.economic_value`.
    """
    if raw is None:
        return None
    from volforecast.evaluation.economic_value import parse_gsvivs_sizing_specs

    return parse_gsvivs_sizing_specs(raw)


_VALID_IV_SOURCES = frozenset({
    "exec_kvar",
    "edrvs_prev_close_1dte",
    "spx_atm_iv_1d",
    "spx_atm_iv_1w",
})


def _parse_gsvivs_iv_sources(raw: Any) -> list[str]:
    """Parse ``gsvivs_iv_sources`` YAML node into a validated list of IV source keys.

    Returns ``["exec_kvar"]`` when the key is absent (None) or empty.
    """
    if raw is None:
        return ["exec_kvar"]
    if not isinstance(raw, list):
        raise ValueError(f"gsvivs_iv_sources must be a list, got {type(raw).__name__}")
    if not raw:
        return ["exec_kvar"]
    for item in raw:
        if item not in _VALID_IV_SOURCES:
            raise ValueError(
                f"Unknown IV source {item!r}. Valid: {sorted(_VALID_IV_SOURCES)}"
            )
    return list(raw)


def _parse_explainability(raw: Any) -> "ExplainabilityConfig":
    """Parse the ``explainability`` YAML node."""
    if raw is None:
        return ExplainabilityConfig()
    return ExplainabilityConfig(
        enabled=bool(raw.get("enabled", False)),
        methods=raw.get("methods", ["treeshap", "ale"]),
        treeshap_max_samples=int(raw.get("treeshap_max_samples", 500)),
        treeshap_interaction=bool(raw.get("treeshap_interaction", False)),
        ale_features=raw.get("ale_features", "top_20"),
        ale_grid_size=int(raw.get("ale_grid_size", 50)),
        models=raw.get("models"),
    )


def _parse_feature_selection(raw: Any) -> "FeatureSelectionConfig | None":
    """Parse the ``feature_selection`` YAML node."""
    if raw is None:
        return None
    return FeatureSelectionConfig(
        enabled=bool(raw.get("enabled", False)),
        method=raw.get("method", "shap_rfe"),
        shadow_features=int(raw.get("shadow_features", 5)),
        threshold_multiplier=float(raw.get("threshold_multiplier", 1.0)),
        min_features=int(raw.get("min_features", 5)),
        max_rounds=int(raw.get("max_rounds", 3)),
        shap_samples=int(raw.get("shap_samples", 500)),
        stability_threshold=float(raw.get("stability_threshold", 0.8)),
    )


def _parse_feature_stack(raw: Any) -> "FeatureStackConfig | None":
    """Parse the ``feature_stack`` YAML node into a FeatureStackConfig."""
    if raw is None:
        return None
    seq_raw = raw.get("sequences")
    sequences = SequenceConfig(**seq_raw) if seq_raw else None
    return FeatureStackConfig(
        source_model=raw["source_model"],
        outputs=raw.get("outputs", ["prediction"]),
        embedding_dim=raw.get("embedding_dim"),
        independent=raw.get("independent", True),
        n_inner_folds=int(raw.get("n_inner_folds", 5)),
        sequences=sequences,
        model_params=raw.get("model_params", {}),
    )


def _parse_blend(raw: Any) -> "BlendConfig | None":
    if raw is None:
        return None
    models = []
    for m in raw["models"]:
        seq = SequenceConfig(**m["sequences"]) if m.get("sequences") else None
        base = None
        if m.get("base_model"):
            base = BaseModelConfig(
                name=m["base_model"]["name"],
                feature_layers=list(m["base_model"].get("feature_layers", []) or []),
                params=dict(m["base_model"].get("params", {}) or {}),
            )
        models.append(BlendSubModelConfig(
            name=m["name"],
            feature_layers=m.get("feature_layers", []),
            params=m.get("params", {}),
            sequences=seq,
            base_model=base,
        ))
    return BlendConfig(
        models=models,
        weight_method=raw.get("weight_method", "inverse_qlike"),
        fixed_weights=raw.get("fixed_weights"),
        regime_indicator=raw.get("regime_indicator"),
        regime_threshold=raw.get("regime_threshold"),
        regime_threshold_type=raw.get("regime_threshold_type", "percentile"),
        val_fraction=float(raw.get("val_fraction", 0.20)),
        val_purge_gap=int(raw.get("val_purge_gap", 10)),
        ridge_alpha=float(raw.get("ridge_alpha", 1.0)),
    )


@dataclass
class ModelConfig:
    """Configuration for a single model."""

    name: str  # registry key (e.g. "har", "lightgbm")
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class BaseModelConfig:
    """Tabular base model for residual / stacked learning.

    Used by sequence models (LSTM/TCN) that learn the residual of a tabular
    base forecast. The base is trained on the same fold's training data and
    its predictions are passed to the sequence model via ``base_preds``.

    Because the base may need a different feature pipeline than the sequence
    model itself (e.g. LightGBM uses many tabular layers while the LSTM
    consumes intraday bars), this config carries its own ``feature_layers``
    list — it is NOT inherited from the top-level ``feature_layers``.

    Per-horizon overrides via ``horizon_overrides[h]['base_model']`` are
    supported and may swap any of ``name``, ``feature_layers``, ``params``.
    See ``ExperimentConfig.base_model_for_horizon``.
    """

    name: str  # registry key (e.g. "har_iv", "lightgbm")
    feature_layers: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class CVConfig:
    """Cross-validation configuration."""

    method: str = (
        "expanding_window"  # purged_kfold | expanding_window | rolling_window | blocked_kfold
    )
    n_splits: int = 5
    purge_gap: int = 5
    # Phase 2.8: post-test exclusion. Indices/dates in [test_end, test_end + embargo)
    # are dropped from the train sets of ALL SUBSEQUENT folds. Independent of purge_gap.
    # Default 0 = no behaviour change vs prior trials.
    embargo: int = 0
    train_size: int | None = None
    test_size: int | None = None


@dataclass
class IngestConfig:
    """Ingestion tuning parameters."""

    workers: int = 4
    batch_size: int = 5
    checkpoint_interval: int = 1
    compute_workers: int | None = None
    symbol_workers: int = 1


@dataclass
class TuningConfig:
    """Hyperparameter tuning configuration (nested CV)."""

    enabled: bool = False
    n_trials: int = 50
    timeout: int | None = 600
    storage_dir: Path | None = None
    inner_cv: CVConfig | None = None  # Defaults to expanding_window with halved train_size
    min_train_size: int = 252  # Skip tuning if outer fold train < this
    tune_every_n_folds: int = 5  # Re-tune every N folds (reuse params in between)
    n_jobs: int = 1  # Parallel Optuna trials (LightGBM releases GIL)
    n_workers: int = 1  # Multi-process Optuna workers (safe: separate LightGBM instances)
    _on_trial_complete: Callable[[int], None] | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    _on_train_progress: Callable[[int, int], None] | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    _on_hpo_event: Callable[[dict], None] | None = field(
        default=None,
        repr=False,
        compare=False,
    )


@dataclass
class ExplainabilityConfig:
    """Configuration for SHAP/ALE explainability in the tournament dashboard."""

    enabled: bool = False
    methods: list[str] = field(default_factory=lambda: ["treeshap", "ale"])
    treeshap_max_samples: int = 500
    treeshap_interaction: bool = False
    ale_features: str | list[str] = "top_20"
    ale_grid_size: int = 50
    models: list[str] | None = None  # None = all tree-based models


@dataclass
class FeatureSelectionConfig:
    """SHAP-based feature selection configuration.

    When enabled, the pipeline performs Boruta-style SHAP feature elimination
    inside each outer CV fold: trains a full-feature model, computes TreeSHAP
    on the validation split, compares feature importance against shadow features,
    and drops features below the threshold before retraining on the pruned set.
    """

    enabled: bool = False
    method: str = "shap_rfe"  # "shap_rfe" (recursive) | "boruta_shap" (single-pass)
    shadow_features: int = 5  # Number of shadow (permuted) features for threshold
    threshold_multiplier: float = 1.0  # Scale factor on max shadow importance
    min_features: int = 5  # Never drop below this many features
    max_rounds: int = 3  # Max elimination rounds (shap_rfe only; boruta_shap uses 1)
    shap_samples: int = 500  # Max samples for TreeSHAP computation per round
    stability_threshold: float = 0.8  # Report features kept in >= this fraction of folds


@dataclass
class TournamentConfig:
    """Tournament-specific settings."""

    models: list[str] = field(default_factory=list)
    mcs_bootstrap: int = 10_000
    model_configs: dict[str, dict[str, Any]] = field(default_factory=dict)
    parallel_models: int = 4  # Max concurrent model workers (ProcessPoolExecutor)
    dh_mode: str = "realistic"  # "realistic" | "discrete" | "simple"
    dh_enabled: bool = True  # enable delta-hedged straddle PnL table + plots
    vt_enabled: bool = True  # enable vol-targeting Sharpe / PnL table + plots
    gsvivs_enabled: bool = True  # enable GSVIVS01 variance swap signal backtest
    gsvivs_short_threshold: float = (
        0.0  # threshold in signal_space units (0 = binary signal, trial-042 optimal)
    )
    gsvivs_default_long: bool = (
        False  # if True, signal is always +1 (long) unless very confident short
    )
    gsvivs_signal_type: str = "iv_rv_gap"  # "iv_rv_gap" | "iv_acceleration"
    gsvivs_flat_percentile: int = 80  # go flat when IV acceleration exceeds this percentile
    gsvivs_iv_source: str = "edrvs"  # "edrvs" (prev-close 1-DTE varswap, no lookahead)
    gsvivs_signal_space: str = "variance"  # "vol" | "variance"
    # 3-mode position-sizing toggle for the GSVIVS dashboard table.
    # ``None`` means "use the project default (binary | asym_long L=2 |
    # zscore L=1)". YAML accepts either a list of dicts with ``mode`` /
    # ``max_leverage`` / ``lookback`` keys, or a list of string shorthands.
    # Resolved to a tuple of :class:`GsvivsSizingSpec` at parse time.
    gsvivs_iv_sources: list[str] = field(default_factory=lambda: ["exec_kvar"])
    gsvivs_sizings: tuple[Any, ...] | None = None
    explainability: ExplainabilityConfig = field(default_factory=ExplainabilityConfig)


@dataclass
class SequenceConfig:
    """Sequence-tensor cache settings for LSTM/TCN models.

    Pipeline.run_pooled consults this when ``model.requires_sequences`` is
    True. Tabular models ignore it entirely.

    Parameters
    ----------
    features : list[str]
        Per-bar feature columns to read from the source parquet, in order.
        Becomes the last axis of the produced tensor.
    max_bars : int
        Padding / truncation target per day.
    sequences_dir : str | None
        Absolute or repo-relative path to the per-symbol parquet directory.
        Defaults to ``data/raw/micro/sequences``.
    cache_dir : str | None
        Where ``{SYMBOL}_{hash}.pt`` tensor caches are persisted. Defaults
        to ``data/processed/sequences``.
    source : str
        Sequence source mode:
        - "parquet": read pre-built intraday bar parquets (default, existing behaviour)
        - "parquet_5min": read 10s bar parquets and aggregate to 5-min bars on-the-fly
        - "parquet_5min_multiday": 5-min bars concatenated across ``lookback_days`` trading days
        - "daily_lookback": build rolling lookback windows from daily panel columns
    lookback_days : int
        Number of trading days to concatenate per sequence when using
        ``parquet_5min_multiday`` source (default 20 → 20×78=1,560 timesteps).
    """

    features: list[str] = field(
        default_factory=lambda: ["log_ret", "vol_share", "buy_ratio", "log_n_trades", "abs_ret"]
    )
    max_bars: int = 2340
    bar_interval: int = 10  # bar interval in seconds (10 = 10s, 300 = 5min)
    sequences_dir: str | None = None
    cache_dir: str | None = None
    norm_mode: str = "pooled"  # "pooled" | "per_symbol"
    source: str = "parquet"  # "parquet" | "daily_lookback"
    lookback_days: int = 20
    context_features: list[str] = field(default_factory=list)


@dataclass
class FeatureStackConfig:
    """Configuration for LSTM/sequence model feature stacking into tabular models.

    When set on ``ExperimentConfig.feature_stack``, the pipeline trains the
    ``source_model`` on intraday sequences per CV fold and injects its outputs
    (prediction, attention statistics, embedding) as additional columns in the
    tabular model's feature matrix.

    Parameters
    ----------
    source_model : str
        Model registry key for the stacking source (e.g. "lstm").
    outputs : list[str]
        Which features to extract. Valid: "prediction", "attention_entropy",
        "attention_peak_time", "embedding".
    embedding_dim : int | None
        If "embedding" in outputs, PCA-reduce to this dimensionality.
        None keeps raw hidden dimension.
    independent : bool
        If True (default), the source model trains without base_preds from
        the tabular model (independent signal). If False, it receives
        base_preds (bidirectional stacking).
    sequences : SequenceConfig | None
        Override sequence config for the stacking source. If None, uses the
        top-level ``sequences`` config.
    model_params : dict
        Hyperparameters for the source model (hidden_dim, n_layers, etc.).
    """

    source_model: str
    outputs: list[str] = field(default_factory=lambda: ["prediction"])
    embedding_dim: int | None = None
    independent: bool = True
    n_inner_folds: int = 5
    sequences: SequenceConfig | None = None
    model_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class BlendSubModelConfig:
    """Configuration for one sub-model in a prediction blend."""
    name: str
    feature_layers: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    sequences: SequenceConfig | None = None
    base_model: BaseModelConfig | None = None


@dataclass
class BlendConfig:
    """Configuration for prediction-level blending of multiple models."""
    models: list[BlendSubModelConfig]
    weight_method: str = "inverse_qlike"
    fixed_weights: list[float] | None = None
    regime_indicator: str | None = None
    regime_threshold: float | None = None
    regime_threshold_type: str = "percentile"
    val_fraction: float = 0.20
    val_purge_gap: int = 10
    ridge_alpha: float = 1.0

    def __post_init__(self):
        if len(self.models) < 2:
            raise ValueError("BlendConfig requires at least 2 models")
        valid_methods = {"fixed", "inverse_qlike", "ridge_meta", "regime_dependent"}
        if self.weight_method not in valid_methods:
            raise ValueError(f"Invalid weight_method {self.weight_method!r}; valid: {sorted(valid_methods)}")
        if self.weight_method == "fixed":
            if self.fixed_weights is None:
                raise ValueError("weight_method='fixed' requires fixed_weights")
            if len(self.fixed_weights) != len(self.models):
                raise ValueError(f"fixed_weights length ({len(self.fixed_weights)}) must match models length ({len(self.models)})")
            if abs(sum(self.fixed_weights) - 1.0) > 1e-6:
                raise ValueError(f"fixed_weights must sum to 1.0, got {sum(self.fixed_weights)}")
        if self.weight_method == "regime_dependent" and not self.regime_indicator:
            raise ValueError("weight_method='regime_dependent' requires regime_indicator")


@dataclass
class ExperimentConfig:
    """Full experiment specification — serializable to/from YAML."""

    name: str
    universe: list[str]
    date_range: tuple[str, str]
    horizons: list[int]
    feature_layers: list[str]  # registry keys: ["har_core", "asymmetry"]
    model: ModelConfig
    cv: CVConfig = field(default_factory=CVConfig)
    tuning: TuningConfig = field(default_factory=TuningConfig)
    ingest: IngestConfig = field(default_factory=IngestConfig)
    tournament: TournamentConfig = field(default_factory=TournamentConfig)
    mode: str = "pipeline"  # pipeline | tournament | ingest
    training_mode: str = "pooled"  # per_symbol | pooled | both
    seed: int = 42
    output_dir: Path = field(default_factory=lambda: Path("data/models"))
    horizon_overrides: dict[int, dict[str, Any]] = field(default_factory=dict)
    sequences: SequenceConfig | dict | None = None
    # Optional tabular base for residual / stacked learning. When set AND
    # ``model.requires_sequences`` is True, the runner fits ``base_model`` on
    # each CV fold's training data and threads its predictions into the
    # sequence model via ``base_preds``. Tabular models ignore this field.
    base_model: BaseModelConfig | None = None
    # Feature stacking: train a sequence model and inject its outputs as
    # columns in the tabular model's feature matrix. See FeatureStackConfig.
    feature_stack: FeatureStackConfig | None = None
    # SHAP-based feature selection. When enabled, each outer CV fold runs
    # Boruta-style SHAP elimination before training the final model.
    feature_selection: FeatureSelectionConfig | None = None
    blend: BlendConfig | None = None
    # Per-fold training cache for sequence models (LSTM/TCN). When enabled,
    # the runner skips fold-level training when an identical fold has been
    # trained before (same config + same train/test dates + same base preds).
    # ``fold_cache_dir`` overrides the default ``data/models/lstm_cache``
    # root; ``None`` keeps the default.
    fold_cache_enabled: bool = True
    fold_cache_dir: str | None = None
    # Number of GPUs for fold-level parallelism in sequence model training.
    # When > 1, the runner dispatches folds to a process pool with one
    # fold per GPU. Does NOT use DDP within a single fold.
    n_gpus: int = 1
    # Conditional (heteroscedastic) Duan correction. When enabled, a second
    # lightweight XGBoost is trained on squared OOS residuals to estimate
    # per-sample forecast variance, then applies σ²(x)/2 correction.
    conditional_duan: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        # Phase 2.7 guard: ``feature_stack`` + per-symbol sequence
        # normalisation is not yet supported. The feature-stack code path in
        # ``volforecast.pipeline.runner`` does NOT thread ``norm_mode``
        # through to the stacked LSTM, so the source model would silently
        # fall back to pooled normalisation and degrade. Fail loud at
        # construction time until Phase 3.12 plumbs ``norm_mode`` through.
        if self.feature_stack is not None:
            def _norm_mode_of(seq: Any) -> str:
                if seq is None:
                    return "pooled"
                if isinstance(seq, dict):
                    return str(seq.get("norm_mode", "pooled"))
                return str(getattr(seq, "norm_mode", "pooled"))

            top_mode = _norm_mode_of(self.sequences)
            fs_mode = _norm_mode_of(getattr(self.feature_stack, "sequences", None))
            if top_mode != "pooled" or fs_mode != "pooled":
                raise ValueError(
                    "feature_stack with sequences.norm_mode != 'pooled' is "
                    "not yet supported (Phase 3.12). The feature-stack code "
                    "path in pipeline/runner.py does not thread norm_mode "
                    "through to the stacked LSTM, which would cause silent "
                    "degradation. Either set sequences.norm_mode='pooled' "
                    "or remove feature_stack."
                )

    def model_params_for_horizon(self, h: int) -> dict[str, Any]:
        """Return model params with horizon-specific overrides merged in."""
        base = dict(self.model.params)
        override = self.horizon_overrides.get(h, {})
        model_override = override.get("model", {}).get("params", {})
        if model_override:
            base.update(model_override)
        # n_gpus is a top-level config field (fold parallelism), not a model
        # parameter. Strip it here for backward compat with old YAML configs
        # that placed it under model.params.
        base.pop("n_gpus", None)
        # Inject blend_config for PredictionBlendModel so any path that
        # instantiates model_cls(**model_params) works correctly.
        if self.model.name == "blend" and self.blend is not None:
            base["blend_config"] = self.blend
        return base

    def cv_for_horizon(self, h: int) -> CVConfig:
        """Return CV config with horizon-specific overrides merged in."""
        override = self.horizon_overrides.get(h, {})
        cv_override = override.get("cv", {})
        if not cv_override:
            return self.cv
        return CVConfig(
            method=cv_override.get("method", self.cv.method),
            n_splits=cv_override.get("n_splits", self.cv.n_splits),
            purge_gap=cv_override.get("purge_gap", self.cv.purge_gap),
            train_size=cv_override.get("train_size", self.cv.train_size),
            test_size=cv_override.get("test_size", self.cv.test_size),
        )

    def base_model_for_horizon(self, h: int) -> BaseModelConfig | None:
        """Return the effective base-model config for horizon ``h``.

        Merge semantics for ``horizon_overrides[h]['base_model']``:
          - If override carries ``name``: replace model class entirely
            (override's ``feature_layers``/``params`` win if present;
            otherwise empty defaults are used — the override is taken as a
            full replacement).
          - Otherwise: keep default ``name`` and ``feature_layers``; merge
            override ``params`` (override wins on key collisions). If
            override carries ``feature_layers``, that list replaces the
            default.

        Returns ``None`` when no base model is configured.
        """
        if self.base_model is None:
            return None
        override = self.horizon_overrides.get(h, {}).get("base_model", {})
        if not override:
            return self.base_model
        if "name" in override and override["name"] != self.base_model.name:
            return BaseModelConfig(
                name=override["name"],
                feature_layers=list(
                    override.get("feature_layers", []) or []
                ),
                params=dict(override.get("params", {}) or {}),
            )
        merged_params = dict(self.base_model.params)
        merged_params.update(override.get("params", {}) or {})
        layers = override.get("feature_layers")
        return BaseModelConfig(
            name=self.base_model.name,
            feature_layers=list(layers) if layers else list(self.base_model.feature_layers),
            params=merged_params,
        )

    def feature_stack_for_horizon(self, h: int) -> FeatureStackConfig | None:
        """Return the effective feature-stack config for horizon ``h``.

        Merge semantics: horizon override dict keys override base config
        values; unspecified keys are inherited from the top-level
        ``feature_stack``. Returns None when no feature_stack is configured.
        """
        if self.feature_stack is None:
            return None
        override = self.horizon_overrides.get(h, {}).get("feature_stack", {})
        if not override:
            return self.feature_stack
        return FeatureStackConfig(
            source_model=override.get("source_model", self.feature_stack.source_model),
            outputs=override.get("outputs", list(self.feature_stack.outputs)),
            embedding_dim=override.get("embedding_dim", self.feature_stack.embedding_dim),
            independent=override.get("independent", self.feature_stack.independent),
            n_inner_folds=override.get("n_inner_folds", self.feature_stack.n_inner_folds),
            sequences=(
                SequenceConfig(**override["sequences"])
                if "sequences" in override
                else self.feature_stack.sequences
            ),
            model_params={**self.feature_stack.model_params, **override.get("model_params", {})},
        )

    @property
    def effective_models(self) -> list[str]:
        """Return tournament model list, inferring from model.name if empty."""
        if self.tournament.models:
            return self.tournament.models
        return [self.model.name]

    @classmethod
    def from_yaml(cls, path: Path) -> ExperimentConfig:
        """Load experiment config from a YAML file."""
        path = Path(path)
        if not path.exists():
            # Resolve relative paths against project root (vol.cmd changes CWD to src/)
            from volforecast.utils.paths import resolve_project_root

            resolved = resolve_project_root() / path
            if resolved.exists():
                path = resolved
        with open(path) as f:
            raw = yaml.safe_load(f)

        # Parse tournament section
        tournament_raw = raw.get("tournament", {})
        tournament_cfg = TournamentConfig(
            models=tournament_raw.get("models", []),
            mcs_bootstrap=tournament_raw.get("mcs_bootstrap", 10_000),
            model_configs=tournament_raw.get("model_configs", {}),
            parallel_models=tournament_raw.get("parallel_models", 4),
            dh_mode=tournament_raw.get("dh_mode", "realistic"),
            dh_enabled=bool(tournament_raw.get("dh_enabled", True)),
            vt_enabled=bool(tournament_raw.get("vt_enabled", True)),
            gsvivs_enabled=tournament_raw.get("gsvivs_enabled", True),
            gsvivs_short_threshold=float(tournament_raw.get("gsvivs_short_threshold", 0.0)),
            gsvivs_default_long=bool(tournament_raw.get("gsvivs_default_long", False)),
            gsvivs_signal_type=tournament_raw.get("gsvivs_signal_type", "iv_rv_gap"),
            gsvivs_flat_percentile=int(tournament_raw.get("gsvivs_flat_percentile", 80)),
            gsvivs_iv_source=tournament_raw.get("gsvivs_iv_source", "edrvs"),
            gsvivs_iv_sources=_parse_gsvivs_iv_sources(tournament_raw.get("gsvivs_iv_sources")),
            gsvivs_signal_space=tournament_raw.get("gsvivs_signal_space", "variance"),
            gsvivs_sizings=_parse_gsvivs_sizings(tournament_raw.get("gsvivs_sizings")),
            explainability=_parse_explainability(tournament_raw.get("explainability")),
        )

        # Parse tuning section
        tuning_raw = raw.get("tuning", {})
        tuning_inner_cv = None
        if "inner_cv" in tuning_raw and tuning_raw["inner_cv"]:
            tuning_inner_cv = CVConfig(**tuning_raw["inner_cv"])
        tuning_storage = Path(tuning_raw["storage_dir"]) if tuning_raw.get("storage_dir") else None
        tuning_cfg = TuningConfig(
            enabled=tuning_raw.get("enabled", False),
            n_trials=tuning_raw.get("n_trials", 50),
            timeout=tuning_raw.get("timeout", 600),
            storage_dir=tuning_storage,
            inner_cv=tuning_inner_cv,
            min_train_size=tuning_raw.get("min_train_size", 252),
            tune_every_n_folds=tuning_raw.get("tune_every_n_folds", 5),
            n_jobs=tuning_raw.get("n_jobs", 1),
            n_workers=tuning_raw.get("n_workers", 1),
        )

        # Parse feature selection section
        feature_selection_cfg = _parse_feature_selection(raw.get("feature_selection"))

        return cls(
            name=raw["name"],
            universe=raw["universe"],
            date_range=tuple(raw["date_range"]),
            horizons=raw["horizons"],
            feature_layers=raw["feature_layers"],
            model=ModelConfig(
                name=raw["model"]["name"],
                params=raw["model"].get("params", {}),
            ),
            cv=CVConfig(**raw.get("cv", {})),
            tuning=tuning_cfg,
            ingest=IngestConfig(**raw.get("ingest", {})),
            tournament=tournament_cfg,
            mode=raw.get("mode", "pipeline"),
            training_mode=raw.get("training_mode", "pooled"),
            seed=raw.get("seed", 42),
            output_dir=Path(raw.get("output_dir", "workspace/tmp/results")),
            horizon_overrides={int(k): v for k, v in raw.get("horizon_overrides", {}).items()},
            sequences=(SequenceConfig(**raw["sequences"]) if raw.get("sequences") else None),
            base_model=(
                BaseModelConfig(
                    name=raw["base_model"]["name"],
                    feature_layers=list(raw["base_model"].get("feature_layers", []) or []),
                    params=dict(raw["base_model"].get("params", {}) or {}),
                )
                if raw.get("base_model")
                else None
            ),
            feature_stack=_parse_feature_stack(raw.get("feature_stack")),
            feature_selection=feature_selection_cfg,
            blend=_parse_blend(raw.get("blend")),
            fold_cache_enabled=bool(raw.get("fold_cache_enabled", True)),
            fold_cache_dir=raw.get("fold_cache_dir"),
            n_gpus=int(raw.get("n_gpus", 1)),
            conditional_duan=raw.get("conditional_duan"),
        )

    def to_yaml(self, path: Path) -> None:
        """Serialize experiment config to a YAML file."""
        data = {
            "mode": self.mode,
            "name": self.name,
            "universe": self.universe,
            "date_range": list(self.date_range),
            "horizons": self.horizons,
            "feature_layers": self.feature_layers,
            "model": {"name": self.model.name, "params": self.model.params},
            "cv": {
                "method": self.cv.method,
                "n_splits": self.cv.n_splits,
                "purge_gap": self.cv.purge_gap,
                "train_size": self.cv.train_size,
                "test_size": self.cv.test_size,
            },
            "ingest": {
                "workers": self.ingest.workers,
                "batch_size": self.ingest.batch_size,
                "checkpoint_interval": self.ingest.checkpoint_interval,
                "compute_workers": self.ingest.compute_workers,
                "symbol_workers": self.ingest.symbol_workers,
            },
            "tuning": {
                "enabled": self.tuning.enabled,
                "n_trials": self.tuning.n_trials,
                "timeout": self.tuning.timeout,
                "storage_dir": str(self.tuning.storage_dir) if self.tuning.storage_dir else None,
                "inner_cv": (
                    {
                        "method": self.tuning.inner_cv.method,
                        "n_splits": self.tuning.inner_cv.n_splits,
                        "purge_gap": self.tuning.inner_cv.purge_gap,
                        "train_size": self.tuning.inner_cv.train_size,
                        "test_size": self.tuning.inner_cv.test_size,
                    }
                    if self.tuning.inner_cv
                    else None
                ),
                "min_train_size": self.tuning.min_train_size,
            },
            "tournament": {
                "models": self.tournament.models,
                "mcs_bootstrap": self.tournament.mcs_bootstrap,
                "gsvivs_iv_sources": self.tournament.gsvivs_iv_sources,
                **(
                    {"model_configs": self.tournament.model_configs}
                    if self.tournament.model_configs
                    else {}
                ),
                **(
                    {"parallel_models": self.tournament.parallel_models}
                    if self.tournament.parallel_models > 1
                    else {}
                ),
            },
            "training_mode": self.training_mode,
            "seed": self.seed,
            "n_gpus": self.n_gpus,
            "output_dir": str(self.output_dir),
        }
        if self.feature_stack is not None:
            fs = self.feature_stack
            fs_data: dict[str, Any] = {
                "source_model": fs.source_model,
                "outputs": fs.outputs,
                "independent": fs.independent,
                "n_inner_folds": fs.n_inner_folds,
            }
            if fs.embedding_dim is not None:
                fs_data["embedding_dim"] = fs.embedding_dim
            if fs.model_params:
                fs_data["model_params"] = fs.model_params
            if fs.sequences is not None:
                fs_data["sequences"] = {
                    "features": fs.sequences.features,
                    "max_bars": fs.sequences.max_bars,
                }
                if fs.sequences.sequences_dir:
                    fs_data["sequences"]["sequences_dir"] = fs.sequences.sequences_dir
                if fs.sequences.cache_dir:
                    fs_data["sequences"]["cache_dir"] = fs.sequences.cache_dir
            data["feature_stack"] = fs_data
        if self.blend is not None:
            bl = self.blend
            bl_models = []
            for m in bl.models:
                m_data: dict[str, Any] = {"name": m.name}
                if m.feature_layers:
                    m_data["feature_layers"] = m.feature_layers
                if m.params:
                    m_data["params"] = m.params
                if m.sequences is not None:
                    m_data["sequences"] = {
                        "features": m.sequences.features,
                        "max_bars": m.sequences.max_bars,
                        "source": m.sequences.source,
                    }
                if m.base_model is not None:
                    m_data["base_model"] = {
                        "name": m.base_model.name,
                        "feature_layers": m.base_model.feature_layers,
                        "params": m.base_model.params,
                    }
                bl_models.append(m_data)
            bl_data: dict[str, Any] = {
                "weight_method": bl.weight_method,
                "val_fraction": bl.val_fraction,
                "val_purge_gap": bl.val_purge_gap,
                "models": bl_models,
            }
            if bl.fixed_weights is not None:
                bl_data["fixed_weights"] = bl.fixed_weights
            if bl.regime_indicator is not None:
                bl_data["regime_indicator"] = bl.regime_indicator
            if bl.regime_threshold is not None:
                bl_data["regime_threshold"] = bl.regime_threshold
                bl_data["regime_threshold_type"] = bl.regime_threshold_type
            if bl.ridge_alpha != 1.0:
                bl_data["ridge_alpha"] = bl.ridge_alpha
            data["blend"] = bl_data
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
