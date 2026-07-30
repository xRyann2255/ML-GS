"""A dark theme built on the base palette."""
from extras.palette import BASE

PALETTE = {k: f"dark-{v}" for k, v in BASE.items()}
