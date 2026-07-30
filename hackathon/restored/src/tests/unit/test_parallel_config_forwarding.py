"""Tests that build_tournament_model_config forwards model-specific flags.

Bug: conditional_duan (a top-level ExperimentConfig field) was silently
dropped when building synthetic tournament configs. Trials 068/068b configured
conditional Duan but it never actually executed.
"""

from __future__ import annotations

import pytest

from volforecast.config import CVConfig, TuningConfig
from volforecast.evaluation._parallel import build_tournament_model_config


@pytest.fixture
def base_kwargs() -> dict:
    """Minimal kwargs for build_tournament_model_config (no data needed)."""
    return dict(
        model_label="har",
        universe=["SPY", "AAPL"],
        date_range=("2020-01-01", "2023-12-31"),
        horizons=[1, 5],
        feature_layers=["layer0_har_core"],
        cv_config=CVConfig(method="expanding_window", n_splits=3, purge_gap=5),
        tuning_config=None,
        model_params=None,
        model_configs=None,
        horizon_overrides=None,
        sequences=None,
        base_model=None,
    )


class TestConditionalDuanForwarding:
    """build_tournament_model_config must preserve conditional_duan."""

    def test_conditional_duan_true_is_forwarded(self, base_kwargs: dict) -> None:
        """When conditional_duan is specified, synthetic config must carry it."""
        duan_cfg = {"n_estimators": 200, "max_depth": 3}
        _, _, config = build_tournament_model_config(
            **base_kwargs, conditional_duan=duan_cfg
        )
        assert config.conditional_duan == duan_cfg

    def test_conditional_duan_none_is_default(self, base_kwargs: dict) -> None:
        """When conditional_duan is not passed, synthetic config has None (backward compat)."""
        _, _, config = build_tournament_model_config(**base_kwargs)
        assert config.conditional_duan is None

    def test_conditional_duan_empty_dict_forwarded(self, base_kwargs: dict) -> None:
        """An empty dict (enabled with defaults) is distinct from None (disabled)."""
        _, _, config = build_tournament_model_config(
            **base_kwargs, conditional_duan={}
        )
        assert config.conditional_duan == {}

    def test_conditional_duan_false_like_value(self, base_kwargs: dict) -> None:
        """If source has a falsy-but-not-None value, synthetic preserves it exactly."""
        # This tests pass-through semantics (not hardcoded to True)
        _, _, config = build_tournament_model_config(
            **base_kwargs, conditional_duan={"enabled": False}
        )
        assert config.conditional_duan == {"enabled": False}
