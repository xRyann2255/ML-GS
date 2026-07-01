#!/usr/bin/env bash
# get-cookie.sh — Obtain a GSSSO cookie and print its value to stdout.
#
# Usage:
#   eval "$(skills/GSSSO_AUTH/src/get-cookie.sh)"
#   # GSSSO is now set in the calling shell
#
# Or capture directly:
#   GSSSO=$(skills/GSSSO_AUTH/src/get-cookie.sh)
#
# Requires: curl, a valid Kerberos ticket (run `kinit` first)
# Output:   Prints the GSSSO cookie value to stdout.
#           On failure, prints an error to stderr and exits non-zero.

set -euo pipefail

SSO_URL="https://authn.web.gs.com/desktopsso/Login"

# --- Check for Kerberos ticket ---
if ! klist -s 2>/dev/null; then
    echo "ERROR: No valid Kerberos ticket found." >&2
    echo "       Run 'kinit' in your terminal first." >&2
    exit 1
fi

# --- Get GSSSO cookie ---
echo "GET ${SSO_URL}" >&2

GSSSO=$(curl -s --negotiate -u : -L -c - "${SSO_URL}" 2>/dev/null | grep GSSSO | awk '{print $NF}')

if [ -z "${GSSSO}" ]; then
    echo "ERROR: Failed to obtain GSSSO cookie." >&2
    echo "       Your Kerberos ticket may be invalid. Try 'kdestroy && kinit'." >&2
    exit 1
fi

printf '%s' "${GSSSO}"
