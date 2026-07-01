"""Slow test configuration.

Slow tests read real data from data/processed/ or data/raw/.
They are excluded from the default pytest run (--ignore=tests/slow in pyproject.toml).
Run explicitly with: uv run pytest tests/slow/
"""
