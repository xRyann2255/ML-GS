"""Summary statistics. Deliberately imports nothing from this repo."""
import math


def mean(values):
    return sum(values) / len(values) if values else 0.0


def stdev(values):
    """Population standard deviation, which is all this fixture needs."""
    if len(values) < 2:
        return 0.0
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / len(values))
