"""Trailhead generator tests — package marker only.

This file exists so that a single test module can be addressed by name:

    cd hackathon && PYTHONPATH=src py -3.11 -m unittest tests.test_survey -v

Without it, `tests` is not an importable package and that command fails with
`ModuleNotFoundError: No module named 'tests.test_survey'` for every module —
a red result that has nothing to do with the code under test. Whole-suite
discovery worked either way:

    cd hackathon && PYTHONPATH=src py -3.11 -m unittest discover -s tests -v

so the only thing this marker buys is the per-module form. It is worth having
because that is the form used while iterating on one stage, and a spurious
failure there invites someone to "fix" code that was already correct.

Deliberately empty of code. Nothing is imported here: `unittest discover`
imports this module before collecting anything under it, so an import of
`trailhead` at this level would turn a missing `PYTHONPATH=src` into a
collection-time explosion instead of the clear per-module ImportError, and
would run package code before any test decides it wants it.

The fixture repos under `tests/repos/` are deliberately NOT packages — the
`__init__.py` files inside them belong to the synthetic repos being surveyed,
not to this test tree. `repos/` itself has no `__init__.py`, which is what
stops discovery from descending into them and trying to import a file whose
whole purpose is to be unparseable.
"""
