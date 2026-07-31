"""The domain model. Nothing in here reads a file or prints anything.

Re-exported with a LEVEL-1 RELATIVE IMPORT from a package __init__, which is
the case plan 3.4 corrects: inside an __init__ one dot means this package, not
the parent, so `.model` must resolve to widget.core.model and never to
widget.model. `restored/` has zero relative imports and can never catch this.
"""
from .model import Widget

__all__ = ["Widget"]
