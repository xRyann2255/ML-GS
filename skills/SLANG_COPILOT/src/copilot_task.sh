#!/usr/bin/env bash
export _PY_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/copilot_setup.py"
export _SKILL="SLANG_COPILOT"
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../_shared/_run.sh" "$@"
