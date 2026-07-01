"""Test per-horizon CV override support in ExperimentConfig."""

from volforecast.config import CVConfig, ExperimentConfig, ModelConfig


def test_cv_for_horizon_returns_base_when_no_override():
    """cv_for_horizon returns the base cv config when no override exists."""
    config = ExperimentConfig(
        name="test",
        universe=["SPY"],
        date_range=("2020-01-01", "2024-12-31"),
        horizons=[1, 5, 22],
        feature_layers=["har_core"],
        model=ModelConfig(name="har"),
        cv=CVConfig(train_size=504, test_size=126, purge_gap=10),
    )
    assert config.cv_for_horizon(1).train_size == 504
    assert config.cv_for_horizon(22).train_size == 504


def test_cv_for_horizon_applies_train_size_override():
    """cv_for_horizon returns overridden train_size for specified horizon."""
    config = ExperimentConfig(
        name="test",
        universe=["SPY"],
        date_range=("2020-01-01", "2024-12-31"),
        horizons=[1, 5, 22],
        feature_layers=["har_core"],
        model=ModelConfig(name="har"),
        cv=CVConfig(train_size=1008, test_size=126, purge_gap=10),
        horizon_overrides={
            22: {"cv": {"train_size": 504}},
        },
    )
    # h=1, h=5 use base train_size
    assert config.cv_for_horizon(1).train_size == 1008
    assert config.cv_for_horizon(5).train_size == 1008
    # h=22 uses overridden train_size
    assert config.cv_for_horizon(22).train_size == 504


def test_cv_for_horizon_preserves_other_fields():
    """cv_for_horizon only overrides specified fields, preserves the rest."""
    config = ExperimentConfig(
        name="test",
        universe=["SPY"],
        date_range=("2020-01-01", "2024-12-31"),
        horizons=[1, 5, 22],
        feature_layers=["har_core"],
        model=ModelConfig(name="har"),
        cv=CVConfig(train_size=1008, test_size=126, purge_gap=10, method="expanding_window"),
        horizon_overrides={
            22: {"cv": {"train_size": 504, "test_size": 63}},
        },
    )
    cv_22 = config.cv_for_horizon(22)
    assert cv_22.train_size == 504
    assert cv_22.test_size == 63
    # Non-overridden fields preserved
    assert cv_22.purge_gap == 10
    assert cv_22.method == "expanding_window"
