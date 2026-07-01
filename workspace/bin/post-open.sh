#!/usr/bin/env bash
# Post-open hook: runs automatically when workspace opens.
# Ensures CUDA-enabled LightGBM .so is in the project venv.
set -euo pipefail

VENV_LGB_SO="src/.venv/lib/python3.11/site-packages/lightgbm/lib/lib_lightgbm.so"
SYSTEM_LGB_SO="/usr/local/lib/python3.11/site-packages/lightgbm/lib/lib_lightgbm.so"

# Only act if both venv and system .so exist
if [[ -f "$VENV_LGB_SO" && -f "$SYSTEM_LGB_SO" ]]; then
    VENV_SIZE=$(stat -c%s "$VENV_LGB_SO" 2>/dev/null || echo 0)
    SYSTEM_SIZE=$(stat -c%s "$SYSTEM_LGB_SO" 2>/dev/null || echo 0)

    # System .so is CUDA-compiled (~120MB); venv .so is CPU-only (~10MB)
    if (( SYSTEM_SIZE > VENV_SIZE * 2 )); then
        cp "$SYSTEM_LGB_SO" "$VENV_LGB_SO"
        echo "[post-open] Copied CUDA LightGBM .so into .venv (${SYSTEM_SIZE} bytes)"
    else
        echo "[post-open] LightGBM .so already CUDA-enabled, skipping"
    fi
else
    echo "[post-open] Skipped LightGBM CUDA patch (venv or system .so not found)"
fi
