"""Tests for lineage_to_mermaid Mermaid graph generator."""
import pytest


class TestLineageToMermaid:
    """Test lineage_to_mermaid pure function."""

    def test_import(self):
        """lineage_to_mermaid is importable from visualization.lineage."""
        from volforecast.visualization.lineage import lineage_to_mermaid

    def test_empty_lineage_returns_empty_string(self):
        """No lineage → empty string (no graph needed)."""
        from volforecast.visualization.lineage import lineage_to_mermaid
        result = lineage_to_mermaid({})
        assert result == ""

    def test_none_lineage_returns_empty_string(self):
        """None values in lineage → empty string."""
        from volforecast.visualization.lineage import lineage_to_mermaid
        result = lineage_to_mermaid({"base_model": None, "feature_stack": None})
        assert result == ""

    def test_base_model_only(self):
        """Base model produces warm-start dashed edge."""
        from volforecast.visualization.lineage import lineage_to_mermaid
        lineage = {
            "base_model": {
                "name": "har_iv_0dte",
                "family": "har",
                "description": "HAR with 0DTE IV",
                "features": ["log_rv_d", "log_rv_w", "log_rv_m", "iv_0dte_atm"],
            },
            "feature_stack": None,
        }
        result = lineage_to_mermaid(lineage)
        assert "flowchart LR" in result
        assert "har_iv_0dte" in result
        assert "-." in result  # Mermaid dashed edge syntax

    def test_feature_stack_only(self):
        """Feature stack produces LSTM→features→model edges."""
        from volforecast.visualization.lineage import lineage_to_mermaid
        lineage = {
            "base_model": None,
            "feature_stack": {
                "source_model": "lstm",
                "outputs": ["prediction", "attention_entropy"],
                "sequence_features": ["log_ret", "vol_share", "buy_ratio", "log_n_trades", "abs_ret"],
                "model_params": {"hidden_dim": 128, "n_layers": 2},
            },
        }
        result = lineage_to_mermaid(lineage)
        assert "flowchart LR" in result
        assert "lstm" in result.lower() or "LSTM" in result
        assert "prediction" in result
        assert "-->" in result  # Mermaid solid edge

    def test_both_base_and_feature_stack(self):
        """Both base_model and feature_stack produces complete graph."""
        from volforecast.visualization.lineage import lineage_to_mermaid
        lineage = {
            "base_model": {
                "name": "har_iv_0dte",
                "family": "har",
                "description": "HAR with 0DTE IV",
                "features": ["log_rv_d", "log_rv_w", "log_rv_m", "iv_0dte_atm"],
            },
            "feature_stack": {
                "source_model": "lstm",
                "outputs": ["prediction", "attention_entropy"],
                "sequence_features": ["log_ret", "vol_share"],
                "model_params": {"hidden_dim": 128, "n_layers": 2},
            },
        }
        result = lineage_to_mermaid(lineage)
        assert "flowchart LR" in result
        assert "har_iv_0dte" in result
        assert "-." in result  # dashed edge for base model
        assert "-->" in result  # solid edge for feature stack

    def test_output_is_valid_mermaid_syntax(self):
        """Output should not contain Python-isms or invalid characters."""
        from volforecast.visualization.lineage import lineage_to_mermaid
        lineage = {
            "base_model": {
                "name": "har_iv_1w",
                "family": "har",
                "description": "HAR + 1-week IV",
                "features": ["log_rv_d", "log_rv_w", "log_rv_m", "iv_1w_atm"],
            },
            "feature_stack": None,
        }
        result = lineage_to_mermaid(lineage)
        # Should not contain Python dict/list syntax
        assert "{" not in result or "}" not in result or "subgraph" in result
        # Should start with flowchart directive
        assert result.strip().startswith("flowchart LR")
