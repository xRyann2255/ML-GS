#!/usr/bin/env bash
# get-cookie_task.sh — Obtain a GSSSO cookie (Linux equivalent of get-cookie_task.cmd).
# Uses curl + Kerberos negotiate (the existing get-cookie.sh logic).
#
# Usage: get-cookie_task.sh [--out-file path/to/cookie.txt]

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---- Parse args ----
OUT_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --out-file) OUT_FILE="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# ---- Delete stale cookie file ----
if [[ -n "$OUT_FILE" && -f "$OUT_FILE" ]]; then
    rm -f "$OUT_FILE"
fi

# ---- Get GSSSO cookie ----
SSO_URL="https://authn.web.gs.com/desktopsso/Login"

if ! klist -s 2>/dev/null; then
    echo "ERROR: No valid Kerberos ticket. Run 'kinit' first." >&2
    exit 0
fi

GSSSO=$(curl -s --negotiate -u : -L -c - "${SSO_URL}" 2>/dev/null | grep GSSSO | awk '{print $NF}')

if [[ -z "$GSSSO" ]]; then
    echo "ERROR: No GSSSO cookie returned" >&2
    exit 0
fi

printf '%s' "$GSSSO"

if [[ -n "$OUT_FILE" ]]; then
    mkdir -p "$(dirname "$OUT_FILE")" 2>/dev/null || true
    printf '%s' "$GSSSO" > "$OUT_FILE"
fi

# ---- Usage logging ----
if [[ -f "${SCRIPT_DIR}/../../_shared/log_usage.sh" ]]; then
    bash "${SCRIPT_DIR}/../../_shared/log_usage.sh" "GSSSO_AUTH"
fi

exit 0
