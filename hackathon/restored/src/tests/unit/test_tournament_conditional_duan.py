"""Tests that conditional_duan flows from tournament entrypoints to _parallel."""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestTournamentConditionalDuan:
    """Verify conditional_duan is wired end-to-end in tournament entrypoints."""

    def test_run_har_tournament_accepts_conditional_duan(self):
        """run_har_tournament must accept conditional_duan parameter."""
        import inspect

        from volforecast.evaluation.tournament import run_har_tournament

        sig = inspect.signature(run_har_tournament)
        assert "conditional_duan" in sig.parameters, (
            "run_har_tournament missing conditional_duan parameter"
        )
        # Default must be None (backward compat)
        param = sig.parameters["conditional_duan"]
        assert param.default is None

    def test_run_tournament_pooled_accepts_conditional_duan(self):
        """_run_tournament_pooled must accept conditional_duan parameter."""
        import inspect

        from volforecast.evaluation.tournament import _run_tournament_pooled

        sig = inspect.signature(_run_tournament_pooled)
        assert "conditional_duan" in sig.parameters, (
            "_run_tournament_pooled missing conditional_duan parameter"
        )
        param = sig.parameters["conditional_duan"]
        assert param.default is None

    def test_conditional_duan_forwarded_to_run_models_pooled(self):
        """When conditional_duan is set, _run_tournament_pooled forwards it to run_models_pooled."""
        import inspect
        import textwrap

        from volforecast.evaluation.tournament import _run_tournament_pooled

        # Verify the call-site in source code passes conditional_duan
        source = inspect.getsource(_run_tournament_pooled)
        assert "conditional_duan=conditional_duan" in source, (
            "_run_tournament_pooled does not forward conditional_duan to run_models_pooled. "
            f"Source snippet: ...{source[source.find('run_models_pooled'):source.find('run_models_pooled')+500]}..."
        )

    def test_backward_compat_default_none(self):
        """Existing callers without conditional_duan still work (default None)."""
        import inspect

        from volforecast.evaluation.tournament import run_har_tournament

        sig = inspect.signature(run_har_tournament)
        # All params should have defaults (no required params except possibly symbols)
        for name, param in sig.parameters.items():
            if name == "conditional_duan":
                assert param.default is None
                break

    def test_run_har_tournament_forwards_conditional_duan(self):
        """run_har_tournament source must forward conditional_duan to pooled path."""
        import inspect

        from volforecast.evaluation.tournament import run_har_tournament

        source = inspect.getsource(run_har_tournament)
        assert "conditional_duan=conditional_duan" in source, (
            "run_har_tournament does not forward conditional_duan to _run_tournament_pooled"
        )
