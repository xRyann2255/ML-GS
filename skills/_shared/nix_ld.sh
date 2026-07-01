#!/usr/bin/env bash
# nix_ld.sh — Source this after setting $PY to configure LD_LIBRARY_PATH
# for nix Python environments. Required for C-extension wheels (numpy, scipy).
#
# Usage: source "path/to/_shared/nix_ld.sh"
# Prerequisite: $PY must be set to the Python interpreter path.

if [[ -z "${LD_LIBRARY_PATH:-}" && -n "${PY:-}" ]]; then
    _PY_STORE="$(readlink -f "$PY" | sed 's|/bin/python.*||')"
    if [[ "$_PY_STORE" == /nix/store/* ]]; then
        while IFS= read -r _dep; do
            if [[ -d "${_dep}/lib" ]]; then
                export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+${LD_LIBRARY_PATH}:}${_dep}/lib"
            fi
        done < <(nix-store --query --references "$_PY_STORE" 2>/dev/null | grep -E "gcc.*lib|zlib")
    fi
    unset _PY_STORE _dep
fi
