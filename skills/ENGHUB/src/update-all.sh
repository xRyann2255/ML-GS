#!/usr/bin/env bash
# Update all already-cloned EngHub doc repos
# Usage: skills/ENGHUB/src/update-all.sh [workspace-root]
set -euo pipefail

WORKSPACE="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
ENGHUB_DIR="$WORKSPACE/workspace/knowledge/enghub"

if [ ! -d "$ENGHUB_DIR" ]; then
  echo "No repos found at $ENGHUB_DIR. Run clone-all.sh first." >&2
  exit 1
fi

for repo_dir in "$ENGHUB_DIR"/*/; do
  if [ -d "$repo_dir/.git" ]; then
    repo_name=$(basename "$repo_dir")
    echo "Updating $repo_name..."
    git -C "$repo_dir" fetch --depth=1 --quiet
    git -C "$repo_dir" reset --hard origin/HEAD --quiet
  fi
done

echo "All repos updated."
