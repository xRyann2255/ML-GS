"""Turn a name into a Widget.

Uses a LEVEL-2 RELATIVE IMPORT from a non-__init__ module, the other half of
the 3.4 correction: parts drop the module itself first, then one more per extra
dot, so `..core.model` from widget.io.loader is widget.core.model.
"""
from ..core.model import Widget

SIZES = {"default": 1, "large": 8}


def load(name):
    return Widget(name=name, size=SIZES.get(name, 0))
