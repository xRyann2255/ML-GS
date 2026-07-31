"""Colour names for parsed records."""
from toolkit.parse import SEPARATOR

BASE = {"ok": "green", "warn": "amber", "bad": "red"}


def colourise(record):
    return [BASE.get(f, "grey") for f in record.split(SEPARATOR)]
