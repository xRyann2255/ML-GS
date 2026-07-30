#!/usr/bin/env bash
# Clone a single EngHub repo by GitLab path
# Usage: skills/ENGHUB/src/clone-one.sh <gitlab-path> [target-dir-name]
# Example: skills/ENGHUB/src/clone-one.sh sdlc-global/cicd-platform-docs
set -euo pipefail

GITLAB_PATH="${1:?Usage: clone-one.sh <gitlab-path> [target-dir-name]}"
REPO_NAME="${2:-$(basename "$GITLAB_PATH")}"
WORKSPACE="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TARGET="$WORKSPACE/workspace/knowledge/enghub/$REPO_NAME"
BASE_URL="https://gitlab.aws.site.gs.com"

mkdir -p "$WORKSPACE/workspace/knowledge/enghub"

if [ -d "$TARGET/.git" ]; then
  echo "Updating $REPO_NAME..."
  git -C "$TARGET" fetch --depth=1 --quiet
  git -C "$TARGET" reset --hard origin/HEAD --quiet
else
  echo "Cloning $REPO_NAME from $GITLAB_PATH..."
  git clone --depth=1 --single-branch "$BASE_URL/$GITLAB_PATH.git" "$TARGET"
fi

echo "Done: $TARGET"
