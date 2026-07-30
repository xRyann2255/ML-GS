#!/usr/bin/env bash
_SHARED="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../_shared" && pwd)"
export _PY_SCRIPT="${_SHARED}/vf_entry.py" _SKILL="FEATURE_BUILD" _VF_MODULE="volforecast.__main__"
exec "${_SHARED}/_run.sh" "$@"
