#!/usr/bin/env bash
# Append a usage entry to the skill usage log.
# Usage: log_usage.sh SKILL_NAME [SOURCE]
#   SKILL_NAME: uppercase skill identifier (e.g., GIT, SLANG_EDIT)
#   SOURCE: "task" (default) or "manual"

SKILL="${1:-}"
[[ -z "$SKILL" ]] && exit 0
SRC="${2:-task}"

SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="${SHARED_DIR}/../../workspace/tmp/skill_usage.log"

TS="$(date -Iseconds)"
echo "${TS} | ${SKILL} | ${SRC}" >> "$LOG"
exit 0
