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

# ---- Save original args for pass-through ----
_ORIG_ARGS=("$@")

# ---- Locate --args-file value early (needed for bootstrap sentinel) ----
_AF=""
_prev=""
for _arg in "$@"; do
    if [[ "$_prev" == "--args-file" ]]; then
        _AF="$_arg"
        break
    fi
    _prev="$_arg"
done

# ---- Python resolution (ledger order; mirrors vol.cmd, AW-54) ----
PY=""

# Step 1: workspace/config/user.json python_path
_UJSON="${ROOT}/workspace/config/user.json"
if [ -z "${PY:-}" ] && [ -f "${_UJSON}" ]; then
    _CAND="$(sed -n 's/.*"python_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "${_UJSON}" | head -n1)"
    [ -n "${_CAND}" ] && [ -x "${_CAND}" ] && PY="${_CAND}"
fi

# Step 2: repo-local venv (existing check, gated on PY unset)
if [[ -z "${PY:-}" && -f "${ROOT}/src/.venv/bin/python" ]]; then
    PY="${ROOT}/src/.venv/bin/python"
fi

# Step 3: python3 / python on PATH
[ -z "${PY:-}" ] && PY="$(command -v python3 || command -v python || true)"

if [[ -z "${PY:-}" ]]; then
    echo "ERROR: No Python found. Checked: user.json python_path, ${ROOT}/src/.venv, PATH." >&2
    [ -n "${_AF:-}" ] && printf 'BOOTSTRAP_FAIL: no Python interpreter (user.json, src/.venv, PATH all empty)\n' > "${_AF}.fail"
    exit 1
fi

# ---- Nix LD_LIBRARY_PATH for C-extension wheels (numpy, scipy) ----
source "${SHARED_DIR}/nix_ld.sh"

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

# ---- AW-41: append EXIT_CODE=<rc> to out_file on post-bootstrap crash ----
if [ "${_EC:-0}" -ne 0 ] && [ -n "${_AF:-}" ]; then
    _OF="$(sed -n 's/.*"out_file"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "${_AF}" 2>/dev/null | head -n1)"
    if [ -z "${_OF}" ]; then
        _OF="$(sed -n 's/.*"output_json"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "${_AF}" 2>/dev/null | head -n1)"
    fi
    if [ -n "${_OF}" ] && [ -f "${_OF}" ] && ! grep -q '^EXIT_CODE=' "${_OF}"; then
        printf 'EXIT_CODE=%s\n' "${_EC}" >> "${_OF}"
    fi
fi

# ---- Usage logging ----
if [[ -f "${SHARED_DIR}/log_usage.sh" ]]; then
    bash "${SHARED_DIR}/log_usage.sh" "${_SKILL:-UNKNOWN}"
fi

# Always exit 0 so VS Code's close:true disposes the terminal.
exit 0
