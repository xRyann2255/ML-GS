"""One rule, so there is something for parse.py to depend on."""


class RuleError(ValueError):
    """Raised when a record does not satisfy a rule."""


def validate(fields):
    if not fields or any(f == "" for f in fields):
        raise RuleError("every field must be non-empty")
    return True
