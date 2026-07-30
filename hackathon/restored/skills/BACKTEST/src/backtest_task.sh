#!/usr/bin/env bash
_SHARED="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../_shared" && pwd)"
export _PY_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/backtest_entry.py" _SKILL="BACKTEST"
exec "${_SHARED}/_run.sh" "$@"
