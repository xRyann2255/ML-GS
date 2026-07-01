#!/usr/bin/env bash
export _PY_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/review.py"
export _SKILL="SLANG_REVIEW"
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../_shared/_run.sh" "$@"
