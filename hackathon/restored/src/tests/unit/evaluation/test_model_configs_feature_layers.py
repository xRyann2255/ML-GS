"""Per-model ``feature_layers`` override via ``tournament.model_configs``.

Plan_096 needs two XGBoost entries in the same tournament (``xgboost_champion``
and ``xgboost_enriched``) with DIFFERENT feature layers. The plumbing carries
that through by letting each ``model_configs`` entry declare its own
``feature_layers`` list, surfaced as the 4th element of ``resolve_model``'s
return tuple.
"""

from __future__ import annotations


class TestResolveModelFeatureLayersOverride:
    def test_entry_with_feature_layers_returns_list(self):
        from volforecast.evaluation._model_utils import resolve_model

        model_configs = {
            "m1": {
                "name": "har",
                "params": {},
                "feature_layers": ["har_core"],
            }
        }
        result = resolve_model("m1", model_configs=model_configs)

        assert len(result) == 4, "resolve_model must return a 4-tuple"
        registry_name, display_label, params, feature_layers_override = result
        assert registry_name == "har"
        assert display_label == "m1"
        assert params == {}
        assert feature_layers_override == ["har_core"]

    def test_entry_without_feature_layers_returns_none(self):
        from volforecast.evaluation._model_utils import resolve_model

        model_configs = {
            "m1": {"name": "har", "params": {}},
        }
        _, _, _, feature_layers_override = resolve_model(
            "m1", model_configs=model_configs
        )
        assert feature_layers_override is None

    def test_plain_label_returns_none_override(self):
        from volforecast.evaluation._model_utils import resolve_model

        _, _, _, feature_layers_override = resolve_model("har")
        assert feature_layers_override is None

    def test_model_params_path_returns_none_override(self):
        from volforecast.evaluation._model_utils import resolve_model

        model_params = {"lightgbm": {"n_estimators": 500}}
        _, _, _, feature_layers_override = resolve_model(
            "lightgbm", model_params=model_params
        )
        assert feature_layers_override is None

    def test_two_xgboost_entries_differ_in_feature_layers(self):
        """The plan_096 use case: same registry name, different layers."""
        from volforecast.evaluation._model_utils import resolve_model

        model_configs = {
            "xgboost_champion": {
                "name": "xgboost",
                "params": {"n_estimators": 100},
                "feature_layers": ["har_core"],
            },
            "xgboost_enriched": {
                "name": "xgboost",
                "params": {"n_estimators": 100},
                "feature_layers": ["har_core", "iv_surface", "cross_asset"],
            },
        }

        champ = resolve_model("xgboost_champion", model_configs=model_configs)
        enr = resolve_model("xgboost_enriched", model_configs=model_configs)

        assert champ[0] == "xgboost" and enr[0] == "xgboost"
        assert champ[1] == "xgboost_champion"
        assert enr[1] == "xgboost_enriched"
        assert champ[3] == ["har_core"]
        assert enr[3] == ["har_core", "iv_surface", "cross_asset"]
