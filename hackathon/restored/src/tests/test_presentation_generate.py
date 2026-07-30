"""Tests for workspace/presentation/generate.py -- dashboard path resolution."""
from pathlib import Path
import tempfile
import os
import shutil
import sys

import pytest

# Make generate importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "workspace" / "presentation"))
import generate


class TestDashboardPathResolution:
    """The --dashboard-path flag should resolve paths relative to CWD (repo root)."""

    def test_cwd_relative_path_resolves(self, tmp_path: Path):
        """Path relative to CWD finds the dashboard and copies it alongside output."""
        # Setup: create a dashboard file at a CWD-relative path
        dashboard_dir = tmp_path / "src" / "data" / "models" / "trial_063" / "plots"
        dashboard_dir.mkdir(parents=True)
        dashboard_file = dashboard_dir / "tournament_dashboard.html"
        dashboard_file.write_text("<html>dash</html>")

        output_dir = tmp_path / "workspace" / "presentation"
        output_dir.mkdir(parents=True)
        output_path = output_dir / "presentation.html"

        # User passes path relative to tmp_path (simulating CWD = repo root)
        cwd_relative = "src/data/models/trial_063/plots/tournament_dashboard.html"

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            html = generate.generate(cwd_relative, output_path)
        finally:
            os.chdir(old_cwd)

        # Should NOT contain the placeholder message
        assert "Dashboard not found at build time" not in html
        # Should contain the iframe
        assert '<iframe id="dashboard-frame"' in html
        # Dashboard should be copied next to output
        assert (output_dir / "tournament_dashboard.html").exists()
        # JS path should be just the filename with cache-buster (no traversal)
        assert '"tournament_dashboard.html?v=' in html

    def test_repo_root_resolution_when_cwd_is_src(self, tmp_path: Path, monkeypatch):
        """When CWD is src/ (as vol script does), repo-root-relative path still resolves."""
        # Setup: simulate repo structure
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        src_dir = repo_root / "src"
        src_dir.mkdir()
        dashboard_dir = repo_root / "src" / "data" / "models" / "trial_063" / "plots"
        dashboard_dir.mkdir(parents=True)
        dashboard_file = dashboard_dir / "tournament_dashboard.html"
        dashboard_file.write_text("<html>dash</html>")

        # generate.py lives at workspace/presentation/generate.py
        presentation_dir = repo_root / "workspace" / "presentation"
        presentation_dir.mkdir(parents=True)
        output_path = presentation_dir / "presentation.html"

        # Monkeypatch __file__ in generate module to point to our fake repo
        fake_generate_py = presentation_dir / "generate.py"
        fake_generate_py.write_text("")
        monkeypatch.setattr(generate, "__file__", str(fake_generate_py))

        # CWD = src/ (what the vol script does), path is repo-root-relative
        old_cwd = os.getcwd()
        try:
            os.chdir(src_dir)  # vol does cd "$SRC"
            html = generate.generate(
                "src/data/models/trial_063/plots/tournament_dashboard.html",
                output_path,
            )
        finally:
            os.chdir(old_cwd)

        assert "Dashboard not found at build time" not in html
        assert '<iframe id="dashboard-frame"' in html
        # Dashboard copied alongside
        assert (presentation_dir / "tournament_dashboard.html").exists()
        assert '"tournament_dashboard.html?v=' in html

    def test_output_relative_path_still_works(self, tmp_path: Path):
        """Legacy behaviour: path relative to output dir still resolves."""
        # Setup: dashboard already sitting next to output
        output_dir = tmp_path / "workspace" / "presentation"
        output_dir.mkdir(parents=True)
        output_path = output_dir / "presentation.html"

        dashboard_file = output_dir / "my_dashboard.html"
        dashboard_file.write_text("<html>dash</html>")

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            html = generate.generate("my_dashboard.html", output_path)
        finally:
            os.chdir(old_cwd)

        assert "Dashboard not found at build time" not in html
        assert '<iframe id="dashboard-frame"' in html

    def test_missing_dashboard_shows_placeholder(self, tmp_path: Path):
        """When dashboard doesn't exist anywhere, placeholder is shown."""
        output_dir = tmp_path / "workspace" / "presentation"
        output_dir.mkdir(parents=True)
        output_path = output_dir / "presentation.html"

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            html = generate.generate("nonexistent/dashboard.html", output_path)
        finally:
            os.chdir(old_cwd)

        assert "Dashboard not found at build time" in html
