#!/usr/bin/env bash
export _PY_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/prime.py"
export _SKILL="PRIME_QUERY"
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../_shared/_run.sh" "$@"
