"""Tests for vol dashboard (dashboard_picker module)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def mock_project(tmp_path: Path):
    """Create a minimal project structure with fake dashboards."""
    # Create models directory with two trial dashboards
    models_dir = tmp_path / "src" / "data" / "models"

    trial_a = models_dir / "trial_001_baseline" / "plots"
    trial_a.mkdir(parents=True)
    (trial_a / "tournament_dashboard.html").write_text("<html>Dashboard A</html>")

    trial_b = models_dir / "trial_002_improved" / "plots"
    trial_b.mkdir(parents=True)
    (trial_b / "tournament_dashboard.html").write_text("<html>Dashboard B</html>")

    # Create metrics.json for trial_b
    metrics_dir = models_dir / "trial_002_improved"
    (metrics_dir / "metrics.json").write_text(
        json.dumps({"h1": {"qlike": 0.1501}, "h5": {"qlike": 0.1320}})
    )

    # A trial dir without dashboard (should be excluded)
    no_dash = models_dir / "trial_003_no_dashboard"
    no_dash.mkdir(parents=True)

    # Create trials.yaml
    research_dir = tmp_path / "workspace" / "research"
    research_dir.mkdir(parents=True)
    (research_dir / "trials.yaml").write_text(
        "trials:\n"
        "- id: trial-001\n"
        "  config: trial_001_baseline.yaml\n"
        "  status: completed\n"
        "- id: trial-002\n"
        "  config: trial_002_improved.yaml\n"
        "  status: completed\n"
    )

    # Create download directory parent
    (tmp_path / "workspace" / "tmp").mkdir(parents=True, exist_ok=True)

    return tmp_path


def test_discover_dashboards(mock_project: Path):
    """Discovers all trial directories that have a dashboard HTML."""
    from volforecast.cli.dashboard_picker import _discover_dashboards

    models_dir = mock_project / "src" / "data" / "models"
    dashboards = _discover_dashboards(models_dir)

    assert len(dashboards) == 2
    names = {d.parent.parent.name for d, _ in dashboards}
    assert names == {"trial_001_baseline", "trial_002_improved"}


def test_copy_dashboard(mock_project: Path):
    """Copies dashboard HTML to workspace/tmp/dashboards/ with correct name."""
    from volforecast.cli.dashboard_picker import copy_dashboard

    dashboard_path = (
        mock_project
        / "src"
        / "data"
        / "models"
        / "trial_001_baseline"
        / "plots"
        / "tournament_dashboard.html"
    )

    dest = copy_dashboard(dashboard_path, project_root=mock_project)

    assert dest.exists()
    assert dest.name == "trial_001_baseline_dashboard.html"
    assert dest.parent.name == "dashboards"
    assert dest.read_text() == "<html>Dashboard A</html>"


def test_pick_and_download_noninteractive(mock_project: Path, monkeypatch):
    """Non-interactive mode copies dashboard by trial name."""
    from volforecast.cli import dashboard_picker

    # Monkeypatch the project root and models dir discovery
    monkeypatch.setattr(dashboard_picker, "_find_project_root", lambda: mock_project)
    monkeypatch.setattr(
        dashboard_picker,
        "_find_models_dir",
        lambda: mock_project / "src" / "data" / "models",
    )

    result = dashboard_picker.pick_and_download_dashboard(
        trial_name="trial_002_improved"
    )

    assert result is not None
    assert result.exists()
    assert "trial_002_improved_dashboard.html" == result.name
    assert result.read_text() == "<html>Dashboard B</html>"


def test_pick_and_download_not_found(mock_project: Path, monkeypatch):
    """Returns None when trial name doesn't exist."""
    from volforecast.cli import dashboard_picker

    monkeypatch.setattr(dashboard_picker, "_find_project_root", lambda: mock_project)
    monkeypatch.setattr(
        dashboard_picker,
        "_find_models_dir",
        lambda: mock_project / "src" / "data" / "models",
    )

    result = dashboard_picker.pick_and_download_dashboard(
        trial_name="nonexistent_trial"
    )

    assert result is None


def test_metrics_preview(mock_project: Path):
    """Metrics preview formats QLIKE numbers from metrics.json."""
    from volforecast.cli.dashboard_picker import _metrics_preview

    metrics_path = (
        mock_project / "src" / "data" / "models" / "trial_002_improved" / "metrics.json"
    )
    preview = _metrics_preview(metrics_path)

    assert "QLIKE=0.1501" in preview
    assert "QLIKE=0.1320" in preview


def test_load_trial_metadata(mock_project: Path):
    """Loads trial metadata keyed by config stem."""
    from volforecast.cli.dashboard_picker import _load_trial_metadata

    meta = _load_trial_metadata(mock_project)

    assert "trial_001_baseline" in meta
    assert meta["trial_001_baseline"]["status"] == "completed"
