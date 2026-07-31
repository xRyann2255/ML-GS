"""Second test file, so the `tests` group is not a one-file group.

A one-file group is what 4.1 rule 3 merges away, and merging tests would take
this repo from four map nodes to three for reasons that have nothing to do with
what it is here to prove.
"""
import unittest

from widget.io.loader import load


class LoadTest(unittest.TestCase):
    def test_an_unknown_name_loads_at_size_zero(self):
        self.assertEqual(load("nope").size, 0)
