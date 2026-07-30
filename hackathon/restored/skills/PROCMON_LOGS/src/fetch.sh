#!/usr/bin/env bash
# fetch.sh — Download procmon logs (.out and/or .err) for a process.
#
# Usage:
#   ./fetch.sh <PROC_NAME> [DATE] [MASTER] [LOG_TYPE] [TAIL_LINES]
#
# Arguments:
#   PROC_NAME    Process path (e.g. pipgit/ldn/intra/ise/prod/RFQ_ISE_Workflow_Server_SDS_Clone~0)
#   DATE         Date in yyyymmdd format (default: today)
#   MASTER       Procmon master (default: eq)
#   LOG_TYPE     "both" (default), "out", or "err"
#   TAIL_LINES   If set, only save the last N lines of each log
#
# Examples:
#   ./fetch.sh pipgit/ldn/intra/ise/prod/RFQ_ISE_Workflow_Server_SDS_Clone~0
#   ./fetch.sh pipgit/ldn/intra/ise/prod/RFQ_ISE_Workflow_Server_SDS_Clone~0 20260313
#   ./fetch.sh pipgit/ldn/intra/ise/prod/RFQ_ISE_Workflow_Server_SDS_Clone~0 20260313 eq out
#   ./fetch.sh pipgit/ldn/intra/ise/prod/RFQ_ISE_Workflow_Server_SDS_Clone~0 20260313 eq both 500
#
# Requires: curl, a valid Kerberos ticket (run `kinit` first)
# Output:   workspace/tmp/procmon-logs/<sanitized_proc_name>-<date>.{out,err}

set -euo pipefail

PROC_NAME="${1:?Usage: $0 <PROC_NAME> [DATE] [MASTER] [LOG_TYPE] [TAIL_LINES]}"
DATE="${2:-$(date +%Y%m%d)}"
MASTER="${3:-eq}"
LOG_TYPE="${4:-both}"
TAIL_LINES="${5:-}"

BASE_URL="http://${MASTER}-log.procmon.services.gs.com:10702/procmonlogs/log/master/${MASTER}/${DATE}/procs/${PROC_NAME}"

# Sanitise process name for the output filename (replace / with _)
SAFE_NAME=$(echo "${PROC_NAME}" | tr '/' '_')

# Resolve workspace root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
OUT_DIR="${WORKSPACE_ROOT}/workspace/tmp/procmon-logs"
mkdir -p "${OUT_DIR}"

fetch_log() {
    local ext="$1"
    local url="${BASE_URL}.${ext}"
    local out_file="${OUT_DIR}/${SAFE_NAME}-${DATE}.${ext}"
    local log_file="${OUT_DIR}/${SAFE_NAME}-${DATE}.${ext}.log"

    echo "GET ${url}" | tee "${log_file}"

    HTTP_CODE=$(curl -s -o "${out_file}" -w "%{http_code}" \
        --negotiate -u : \
        "${url}")
    echo "HTTP ${HTTP_CODE}" | tee -a "${log_file}"

    if [[ "${HTTP_CODE}" -eq 404 ]]; then
        rm -f "${out_file}"
        echo "  .${ext}: not found (404)"
        return 0
    fi

    if [[ "${HTTP_CODE}" -ne 200 ]]; then
        BODY=$(head -c 500 "${out_file}" 2>/dev/null || echo "(empty)")
        rm -f "${out_file}"
        echo "  .${ext}: ERROR HTTP ${HTTP_CODE} — ${BODY}" >&2
        return 1
    fi

    # Apply tail if requested
    if [ -n "${TAIL_LINES}" ]; then
        tail -n "${TAIL_LINES}" "${out_file}" > "${out_file}.tmp"
        mv "${out_file}.tmp" "${out_file}"
    fi

    # Report size
    local size
    size=$(wc -c < "${out_file}" | tr -d ' ')
    local lines
    lines=$(wc -l < "${out_file}" | tr -d ' ')

    local human_size
    if [[ "${size}" -gt 1048576 ]]; then
        human_size="$(( size / 1048576 ))MB"
    elif [[ "${size}" -gt 1024 ]]; then
        human_size="$(( size / 1024 ))KB"
    else
        human_size="${size}B"
    fi

    echo "  .${ext}: ${lines} lines (${human_size}) → ${out_file}"
}

echo "Process: ${PROC_NAME}"
echo "Date:    ${DATE}"
echo "Master:  ${MASTER}"
[ -n "${TAIL_LINES}" ] && echo "Tail:    last ${TAIL_LINES} lines"
echo ""

case "${LOG_TYPE}" in
    both)
        fetch_log "out"
        fetch_log "err"
        ;;
    out)
        fetch_log "out"
        ;;
    err)
        fetch_log "err"
        ;;
    *)
        echo "ERROR: LOG_TYPE must be 'both', 'out', or 'err'" >&2
        exit 1
        ;;
esac
