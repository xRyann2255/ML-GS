"""The Widget record itself. Imports nothing from this repo, so it is the sink."""
import dataclasses


@dataclasses.dataclass(frozen=True)
class Widget:
    name: str
    size: int

    @staticmethod
    def describe(widget):
        return f"{widget.name} ({widget.size})"


def default_settings():
    """A DANGLING import: widget.config has no file on disk anywhere in this repo.

    Deliberately inside a function body so it never runs at import time -- the
    module still imports cleanly, exactly as restored's 706 dangling statements
    do, while survey.dangling gets a target to report.
    """
    from widget.config import SETTINGS

    return SETTINGS
