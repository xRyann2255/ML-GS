#!/usr/bin/env bash
# BACKTEST task wrapper (Linux). Activates venv and runs python -m volforecast.evaluation.economic_value.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# ---- Python from project venv ----
PY=""
if [[ -f "${ROOT}/src/.venv/bin/python" ]]; then
    PY="${ROOT}/src/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PY="$(command -v python3)"
fi
if [[ -z "$PY" ]]; then
    echo "ERROR: No Python interpreter found" >&2
    exit 1
fi

# ---- Nix LD_LIBRARY_PATH for C-extension wheels ----
_SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../_shared" && pwd)"
source "${_SHARED_DIR}/nix_ld.sh"
unset _SHARED_DIR

# ---- Parse --args-file ----
ARGS_FILE=""
_prev=""
for _arg in "$@"; do
    if [[ "$_prev" == "--args-file" ]]; then
        ARGS_FILE="$_arg"
        break
    fi
    _prev="$_arg"
done

if [[ -z "$ARGS_FILE" ]]; then
    echo "ERROR: --args-file is required" >&2
    exit 1
fi
if [[ ! -f "$ARGS_FILE" ]]; then
    echo "ERROR: args file not found: $ARGS_FILE" >&2
    exit 1
fi

# ---- Delete stale output ----
"$PY" -c "
import json, os, sys
a = json.load(open(sys.argv[1]))
for k in ('out_file', 'output_json'):
    f = a.get(k, '')
    if f and os.path.isfile(f):
        os.remove(f)
" "$ARGS_FILE" 2>/dev/null || true

# ---- Run ----
"$PY" -m volforecast.evaluation.economic_value --args-file "$ARGS_FILE"

# ---- Usage logging ----
if [[ -f "${SCRIPT_DIR}/../../_shared/log_usage.sh" ]]; then
    bash "${SCRIPT_DIR}/../../_shared/log_usage.sh" "BACKTEST"
fi

# Always exit 0 so VS Code's close:true disposes the terminal.
exit 0
