"""Named `secrets`, which is also stdlib. `known` is per import root, so this
shadows the stdlib module for pkg/crlf.py and for nothing outside this repo.
"""


def token_hex(n=16):
    return "de" * n
