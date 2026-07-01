#!/usr/bin/env bash
export _PY_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/inspect.py"
export _SKILL="SLANG_REVIEW_INSPECT"
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../_shared/_run.sh" "$@"
