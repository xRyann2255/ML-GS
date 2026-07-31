"""Report formatting. Also imports nothing from this repo -- that is the point."""
import textwrap


class Report:
    """A title and some lines, wrapped to a fixed width."""

    def __init__(self, title, width=72):
        self.title = title
        self.width = width
        self.lines = []

    def add(self, line):
        self.lines.append(line)
        return self

    def render(self):
        body = "\n".join(textwrap.fill(x, self.width) for x in self.lines)
        return f"{self.title}\n{'=' * len(self.title)}\n{body}"
