#!/usr/bin/env bash
export _PY_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/nds.py"
export _SKILL="NDS_INFRA"
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../_shared/_run.sh" "$@"
