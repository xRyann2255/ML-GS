#!/usr/bin/env bash
# git_task.sh — Generic git command wrapper (Linux equivalent of git_task.cmd).
# Reads --args-file JSON and runs git.
#
# Args JSON (single command):
#   { "args": ["status", "--short"], "out_file": "workspace/tmp/git_out.txt" }
#
# Args JSON (compound — multiple commands in sequence):
#   { "steps": [["add","-A"],["commit","-m","msg"],["push"]], "out_file": "..." }

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# ---- Prevent editor-blocking on rebase/merge/commit --amend ----
export GIT_MERGE_AUTOEDIT=no
export GIT_EDITOR=true
export GIT_SEQUENCE_EDITOR=true

# ---- Python for JSON parsing ----
PY=""
if [[ -f "${ROOT}/src/.venv/bin/python" ]]; then
    PY="${ROOT}/src/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PY="$(command -v python3)"
elif command -v python &>/dev/null; then
    PY="$(command -v python)"
fi

if [[ -z "$PY" ]]; then
    echo "ERROR: No Python interpreter found" >&2
    exit 1
fi

# ---- Parse --args-file ----
ARGS_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --args-file) ARGS_FILE="$2"; shift 2 ;;
        *) shift ;;
    esac
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
f = a.get('out_file', '')
if f and os.path.isfile(f):
    os.remove(f)
" "$ARGS_FILE" 2>/dev/null || true

# ---- Run git commands via Python (handles JSON parsing + sequencing) ----
"$PY" -c "
import json, subprocess, sys, os

args_file = sys.argv[1]
a = json.load(open(args_file))
all_out = []
ec = 0

if 'steps' in a:
    for i, step in enumerate(a['steps'], 1):
        header = f'--- step {i}: git {\" \".join(step)} ---'
        print(header)
        all_out.append(header)
        result = subprocess.run(['git'] + list(step), capture_output=True, text=True)
        text = result.stdout + result.stderr
        print(text, end='')
        all_out.append(text)
        ec = result.returncode
        if ec != 0:
            fail_msg = f'--- FAILED (exit {ec}) at step {i} ---'
            print(fail_msg)
            all_out.append(fail_msg)
            break
else:
    git_args = list(a.get('args', []))
    result = subprocess.run(['git'] + git_args, capture_output=True, text=True)
    text = result.stdout + result.stderr
    print(text, end='')
    all_out.append(text)
    ec = result.returncode

out_file = a.get('out_file', '')
if out_file:
    os.makedirs(os.path.dirname(out_file) if os.path.dirname(out_file) else '.', exist_ok=True)
    with open(out_file, 'w') as f:
        f.write('\n'.join(all_out))

sys.exit(ec)
" "$ARGS_FILE"
_EC=$?

# ---- Usage logging ----
if [[ -f "${SCRIPT_DIR}/../../_shared/log_usage.sh" ]]; then
    bash "${SCRIPT_DIR}/../../_shared/log_usage.sh" "GIT"
fi

# Always exit 0 so VS Code's close:true disposes the terminal.
exit 0
