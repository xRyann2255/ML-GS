"""Every line of this file ends \r\n. Nothing else about it is unusual."""
import secrets

WIDTH = 80


def token(n=16):
    """Reaches the SHADOWING module `secrets.py` next door, not the stdlib."""
    return secrets.token_hex(n)
