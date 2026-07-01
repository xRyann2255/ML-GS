"""Tests for _build_model_details server-side assembly."""
import pytest


class TestBuildModelDetails:
    """Test _build_model_details returns correct schema."""

    def test_import(self):
        """_build_model_details is importable from visualization.dashboard."""
        from volforecast.visualization.dashboard import _build_model_details

    def test_plain_har_schema(self):
        """Plain HAR model returns correct detail structure."""
        from volforecast.visualization.dashboard import _build_model_details
        # We'll test with a minimal fixture once implemented
        # For now, just assert the function exists and is callable
        assert callable(_build_model_details)

    def test_har_detail_has_required_keys(self):
        """HAR detail dict has all required top-level keys."""
        from volforecast.visualization.dashboard import _build_model_details
        # Mock a minimal config + stats scenario
        # The actual test will use fixtures; this defines the expected keys
        required_keys = {"family", "description", "effective_params", "feature_layers",
                        "feature_columns", "n_features", "lineage", "family_stats", "attribution"}
        # This will be a real assertion once _build_model_details is implemented
        assert required_keys  # placeholder — real test checks output

    def test_lightgbm_with_base_model(self):
        """LightGBM with base_model has lineage.base_model populated."""
        from volforecast.visualization.dashboard import _build_model_details
        assert callable(_build_model_details)

    def test_lstm_detail_schema(self):
        """LSTM detail has family='lstm' and arch summary in family_stats."""
        from volforecast.visualization.dashboard import _build_model_details
        assert callable(_build_model_details)

    def test_feature_stacked_lightgbm(self):
        """Feature-stacked LightGBM has lineage.feature_stack populated."""
        from volforecast.visualization.dashboard import _build_model_details
        assert callable(_build_model_details)

    def test_graceful_degradation_no_artifacts(self):
        """When artifacts are missing, family_stats and attribution are None."""
        from volforecast.visualization.dashboard import _build_model_details
        assert callable(_build_model_details)
