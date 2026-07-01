#!/usr/bin/env bash
# _run.sh — Shared bootstrap for Python-based VS Code tasks (Linux).
#
# The calling wrapper must set two env vars before calling:
#   _PY_SCRIPT  = absolute path to the Python entry point
#   _SKILL      = uppercase skill name for usage logging
#
# Example wrapper (3 lines):
#   #!/usr/bin/env bash
#   export _PY_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/query.py"
#   export _SKILL="CANVAS"
#   exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../_shared/_run.sh" "$@"
#
# This script handles:
#   1. Python venv auto-detection (src/.venv or system python3)
#   2. Args-file existence validation (fail fast)
#   3. Stale output cleanup (deletes out_file/output_json before run)
#   4. Python script execution
#   5. Usage logging via log_usage.sh

set -uo pipefail

if [[ -z "${_PY_SCRIPT:-}" ]]; then
    echo "ERROR: _PY_SCRIPT not set" >&2
    exit 1
fi

SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SHARED_DIR}/../.." && pwd)"

# ---- Python detection ----
PY=""
if [[ -f "${ROOT}/src/.venv/bin/python" ]]; then
    PY="${ROOT}/src/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PY="$(command -v python3)"
elif command -v python &>/dev/null; then
    PY="$(command -v python)"
fi

if [[ -z "$PY" ]]; then
    echo "ERROR: No Python interpreter found (checked src/.venv/bin/python, python3, python)" >&2
    exit 1
fi

# ---- Nix LD_LIBRARY_PATH for C-extension wheels (numpy, scipy) ----
source "${SHARED_DIR}/nix_ld.sh"

# ---- Save original args for pass-through ----
_ORIG_ARGS=("$@")

# ---- Locate --args-file value (without consuming args) ----
_AF=""
_prev=""
for _arg in "$@"; do
    if [[ "$_prev" == "--args-file" ]]; then
        _AF="$_arg"
        break
    fi
    _prev="$_arg"
done

# ---- Validate args-file & clean stale output ----
if [[ -n "$_AF" ]]; then
    if [[ ! -f "$_AF" ]]; then
        echo "ERROR: args file not found: $_AF" >&2
        exit 1
    fi
    # Delete stale output so agent never reads old data on failure
    "$PY" -c "
import json, os, sys
a = json.load(open(sys.argv[1]))
for k in ('out_file', 'output_json'):
    f = a.get(k, '')
    if f and os.path.isfile(f):
        os.remove(f)
" "$_AF" 2>/dev/null || true
fi

# ---- Run ----
"$PY" "$_PY_SCRIPT" "${_ORIG_ARGS[@]}"
_EC=$?

# ---- Usage logging ----
if [[ -f "${SHARED_DIR}/log_usage.sh" ]]; then
    bash "${SHARED_DIR}/log_usage.sh" "${_SKILL:-UNKNOWN}"
fi

# Always exit 0 so VS Code's close:true disposes the terminal.
exit 0
