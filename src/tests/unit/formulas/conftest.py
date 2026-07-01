"""Formula test fixtures — known-answer inputs for exact verification."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

GOLD_DIR = Path(__file__).parent / "gold_values"


@pytest.fixture
def load_gold():
    """Factory fixture: load a gold-value JSON file by name."""

    def _load(filename: str) -> dict:
        path = GOLD_DIR / filename
        return json.loads(path.read_text())

    return _load
