"""Split a record string into fields and hand it to the rule checker."""
from toolkit.rules.check import validate

SEPARATOR = "|"


def parse(record):
    fields = [f.strip() for f in record.split(SEPARATOR)]
    validate(fields)
    return fields
