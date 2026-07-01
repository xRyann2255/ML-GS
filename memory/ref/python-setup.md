---
created: 2026-02-28
updated: 2026-05-19
tags: [setup, python, uv, environment]
status: active
relates:
  - ref/devtools.md
---

# Python Project Setup

Python at GS uses **uv** (via devtools). Replaces pip, venv, setuptools.

**All deps in `pyproject.toml`.** Always `uv add <pkg>` then `uv run python script.py`.
**Never `uv run --with`** for native/compiled packages — ephemeral env breaks post-install steps.

## Running uv

- **Windows:** `cmd /c "H:\uv-env.cmd && uv run python script.py"` (not on PATH)
- **Linux (Coder workspace):** `uv` on PATH via nix (`nix-env -iA nixpkgs.uv`). Python 3.11 via nix.

## Quick Reference

```bash
uv sync                         # Create/update .venv + install deps
uv run python my_script.py      # Run inside .venv
uv add fastapi uvicorn           # Add runtime dep
uv add --dev pytest              # Add dev dep
uv init --name my-proj --python 3.13  # New project
```

## pyproject.toml

```toml
[project]
name = "my-project"
version = "1.0.0"
requires-python = ">=3.12"
dependencies = []
```

Use `>=3.12` not pinned version. `uv run` auto-uses `.venv` — no activation needed.

Dependencies go into `pyproject.toml` and resolve into `uv.lock`.

## Directory Structure

```
my-project/
├── pyproject.toml
├── uv.lock
├── my_project/
│   ├── __init__.py
│   └── main.py
└── .venv/
```

## Quick Reference

| What                       | Command                            |
| -------------------------- | ---------------------------------- |
| Check if uv is installed   | `devtools ls uv`                   |
| Install uv                 | `devtools install uv`              |
| Create venv + install deps | `uv sync`                          |
| Add a dependency           | `uv add <package>`                 |
| Add a dev dependency       | `uv add --dev <package>`           |
| Run a script               | `uv run python script.py`          |
| Run as module              | `uv run python -m my_project.main` |
| Update all dependencies    | `uv lock --upgrade && uv sync`     |

## Unified Environment (Resolved 2026-05-11)

Single `uv run` command serves both ML development and GS data access.

### Architecture

```
src/.venv/                         (uv-managed, Python 3.12)
├── Lib/site-packages/             (numpy, pandas, scipy, sklearn, volforecast, etc.)
│   └── _venv312.pth              → H:\venv312\Lib\site-packages
└── pyvenv.cfg                     (home = H:\venv312\Scripts)
```

The `.pth` file adds venv312's site-packages to `sys.path`, making GS-provisioned packages visible without `--system-site-packages` (which doesn't work here because venv312 is itself a venv, not a real install).

### What's accessible via `uv run`

| Package | Source | Version |
|---------|--------|---------|
| volforecast | uv (editable install) | 0.2.0 |
| numpy, pandas, scipy, sklearn | uv (from internal PyPI) | latest 3.12-compatible |
| goldmansachs.pyslang | venv312 via .pth | 1.0.13 |
| pytickclient | venv312 via .pth | (system-provisioned) |
| gs_quant, gs_quant_internal | venv312 via .pth | (system-provisioned) |

### Import patterns

```python
# GS packages (note: "import pyslang" does NOT work — use the namespace)
import goldmansachs.pyslang as pyslang
pyslang.start(subprocess=True, object_database="Equity")

from pytickclient import query
from gs_quant_internal.tsdb import TSDBSymbol
```

### How it was set up

```powershell
# 1. pyproject.toml: requires-python = ">=3.10,<3.13"
# 2. Recreate venv from venv312's Python (gives 3.12):
uv venv --python H:\venv312\Scripts\python.exe
# 3. Re-lock and install:
uv lock && uv sync
# 4. Bridge GS packages:
echo H:\venv312\Lib\site-packages > src/.venv/Lib/site-packages/_venv312.pth
```

### Maintenance

- **After `uv sync`:** The `.pth` file survives — `uv sync` adds/removes declared deps but doesn't purge unknown files.
- **After venv deletion (`rm .venv`):** Must re-run setup steps 2-4 above. The `.pth` file lives inside `.venv` so it's lost on deletion.
- **Adding new deps:** `uv add <package>` then `uv sync` as normal.
- **`vol test`, `vol lint`, `vol run`:** All work via the unified `uv run` — no special handling needed.

## Linux (Coder): Nix LD_LIBRARY_PATH

On Linux Coder workspaces, Python is from nix (glibc 2.40). Pip-installed manylinux wheels (numpy, scipy) link against `libstdc++.so.6` and `libz.so.1` which are in the nix store but not on the default search path.

### Solution

Set `LD_LIBRARY_PATH` to include nix's gcc-lib and zlib — but NOT glibc (Python's RUNPATH handles glibc; adding it to LD_LIBRARY_PATH breaks manylinux binaries like ruff).

```bash
# Derive paths from nix python's dependencies:
PY_STORE="$(readlink -f "$(command -v python3)" | sed 's|/bin/python3.*||')"
nix-store --query --references "$PY_STORE" | grep -E "gcc.*lib|zlib"
# → /nix/store/...-gcc-14.3.0-lib
# → /nix/store/...-zlib-1.3.1
export LD_LIBRARY_PATH="/nix/store/...-gcc-14.3.0-lib/lib:/nix/store/...-zlib-1.3.1/lib"
```

### Implementation

- `vol` script: Sets `_NIX_PY_LD_PATH` and prefixes it only for python commands (not ruff/uv)
- `skills/_shared/nix_ld.sh`: Sourceable snippet that exports `LD_LIBRARY_PATH` for Python tasks
- `skills/_shared/_run.sh`: Sources `nix_ld.sh` automatically
- Bespoke ML wrappers: Source `nix_ld.sh` after Python detection

### Key rule

NEVER add `/usr/lib64` or nix glibc to `LD_LIBRARY_PATH`. System glibc is too old (RHEL 8 = 2.28); nix glibc breaks system binaries. Only export gcc-lib + zlib.
