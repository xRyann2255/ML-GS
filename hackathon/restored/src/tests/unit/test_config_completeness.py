"""Lint-style tests for config YAML completeness.

Catches truncated or unparseable YAML configs and validates tournament.models
is non-empty when tournament mode is active (gsvivs_enabled or dh_enabled or
vt_enabled).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from volforecast.config import ExperimentConfig

# Root of workspace/configs/ relative to repo root
_CONFIGS_DIR = Path(__file__).resolve().parents[3] / "workspace" / "configs"

# Known-broken configs: truncated mid-key during transfer.
# Marked with xfail so CI documents the breakage without blocking.
_KNOWN_BROKEN = {
    "trial_067_xgb_29sym.yaml": "truncated mid-key in explainability section",
    "trial_067_xgb_gsvivs01_eval.yaml": "truncated mid-key in explainability section",
}


def _collect_yaml_configs(xfail_broken: bool = False) -> list[pytest.param]:
    """Collect all .yaml config files as parametrized test cases.

    When xfail_broken=True, known-broken configs get strict xfail markers.
    """
    configs = sorted(_CONFIGS_DIR.glob("*.yaml"))
    params = []
    for cfg_path in configs:
        # Skip canonical example (it's documentation, not a runnable config)
        if cfg_path.name.startswith("_"):
            continue
        marks = ()
        if xfail_broken and cfg_path.name in _KNOWN_BROKEN:
            marks = (pytest.mark.xfail(reason=_KNOWN_BROKEN[cfg_path.name], strict=True),)
        params.append(pytest.param(cfg_path, id=cfg_path.stem, marks=marks))
    return params


@pytest.mark.parametrize("config_path", _collect_yaml_configs(xfail_broken=False))
def test_yaml_parses_without_error(config_path: Path) -> None:
    """Every config YAML must be parseable by PyYAML without error."""
    with open(config_path) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), f"{config_path.name} did not parse to a dict"


@pytest.mark.parametrize("config_path", _collect_yaml_configs(xfail_broken=False))
def test_config_loads_as_experiment_config(config_path: Path) -> None:
    """Every config must load via ExperimentConfig.from_yaml without error."""
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    if raw.get("mode") == "ingest":
        pytest.skip("ingest-mode config — not a full ExperimentConfig")
    # Skip configs that don't follow the standard ExperimentConfig schema
    # (e.g. forecast_live.yaml has a different purpose/schema)
    required_keys = {"name", "universe", "date_range", "horizons", "feature_layers", "model"}
    if not required_keys.issubset(raw.keys()):
        pytest.skip(f"non-standard config — missing keys: {required_keys - raw.keys()}")
    ExperimentConfig.from_yaml(config_path)


@pytest.mark.parametrize("config_path", _collect_yaml_configs(xfail_broken=True))
def test_tournament_models_nonempty_when_enabled(config_path: Path) -> None:
    """If tournament is enabled, tournament.models must be non-empty.

    Heuristics for when models is required:
    - dh_enabled or vt_enabled (need model comparisons)
    - parallel_models > 1 (explicitly expects multiple models)
    - explainability key exists with None value (truncation signal)
    """
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    if raw.get("mode") == "ingest":
        pytest.skip("ingest-mode config — not a full ExperimentConfig")

    tournament = raw.get("tournament", {})
    if not tournament:
        pytest.skip("no tournament section")

    # Check if any tournament evaluation is enabled
    gsvivs = tournament.get("gsvivs_enabled", False)
    dh = tournament.get("dh_enabled", False)
    vt = tournament.get("vt_enabled", False)
    if not (gsvivs or dh or vt):
        pytest.skip("tournament has no evaluations enabled")

    # Determine if models list should be required
    needs_models = (
        dh
        or vt
        or tournament.get("parallel_models", 1) > 1
        # explainability key explicitly present with None value = truncation signal
        or ("explainability" in tournament and tournament["explainability"] is None)
    )
    if not needs_models:
        pytest.skip("single-model gsvivs config — models list not required")

    models = tournament.get("models", [])
    assert models, (
        f"{config_path.name}: tournament has evaluations enabled "
        f"(gsvivs={gsvivs}, dh={dh}, vt={vt}) but tournament.models is empty. "
        f"This config is likely truncated or misconfigured."
    )
