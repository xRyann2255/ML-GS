#!/usr/bin/env bash
export _PY_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lint_all.py"
export _SKILL="LINT"
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../skills/_shared/_run.sh" "$@"
