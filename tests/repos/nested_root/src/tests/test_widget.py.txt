"""Lives at src/tests -- inside the import root, outside the declared package."""
import unittest

from widget.core.model import Widget


class DescribeTest(unittest.TestCase):
    def test_describe_names_the_widget_and_its_size(self):
        self.assertEqual(Widget.describe(Widget("bolt", 3)), "bolt (3)")
