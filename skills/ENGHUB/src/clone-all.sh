#!/usr/bin/env bash
# Clone or update all EngHub doc repos into workspace/knowledge/enghub/
# Usage: skills/ENGHUB/src/clone-all.sh [workspace-root]
set -euo pipefail

WORKSPACE="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
ENGHUB_DIR="$WORKSPACE/workspace/knowledge/enghub"
BASE_URL="https://gitlab.aws.site.gs.com"

mkdir -p "$ENGHUB_DIR"

clone_or_update() {
  local gitlab_path="$1"
  local repo_name
  repo_name=$(basename "$gitlab_path")
  local target="$ENGHUB_DIR/$repo_name"

  if [ -d "$target/.git" ]; then
    echo "Updating $repo_name..."
    git -C "$target" fetch --depth=1 --quiet
    git -C "$target" reset --hard origin/HEAD --quiet
  else
    echo "Cloning $repo_name..."
    git clone --depth=1 --single-branch "$BASE_URL/$gitlab_path.git" "$target"
  fi
}

# CI/CD & Developer Experience
clone_or_update "sdlc-global/cicd-platform-docs"
clone_or_update "developer-experience/enghub-happy-paths/set-up-infrastructure"
clone_or_update "developer-experience/enghub-happy-paths/working-with-python"
clone_or_update "developer-experience/enghub-happy-paths/enghub-solutions"
clone_or_update "developer-experience/well-architected/well-architected-platform-docs"

# IAM
clone_or_update "iam/iam-docs"
clone_or_update "developer-experience/enghub-happy-paths/application-entitlement-management"
clone_or_update "developer-experience/enghub-happy-paths/demise-webid"

# Cloud
clone_or_update "derun/sky/cloud-platform-docs"
clone_or_update "infra/container-runtime/fi-docs"

# Foundational Infra
clone_or_update "foundational-infra/dynamic-computing/dc-enghub"
clone_or_update "foundational-infra/computing-and-development-platform-engineering/converge-docs"
clone_or_update "foundational-infra/inventory-management/inventory-central-enghub"
clone_or_update "derun/unixeng/linux-image-enghub-docs"
clone_or_update "infra/luma/luma-enghub"
clone_or_update "derun/dev-desktop/dev-desktop-docs"

# Storage
clone_or_update "foundational-infra/storage-products/storage-cdot-enghub"
clone_or_update "foundational-infra/storage-products/storage-fourier-enghub"
clone_or_update "foundational-infra/storage-products/storage-onpremobs-enghub"

# Observability
clone_or_update "sre/playground/obs-and-rel-platform-docs"

# AI & Data
clone_or_update "dsml/nlp/nlp-platform-enghub-documentation"
clone_or_update "data-engineering/alloy/alloy-platform-docs"
clone_or_update "quantumeng/quantum-data-discovery/quantum-docs"
clone_or_update "developer-experience/enghub-happy-paths/ai-program-office"

# Web
clone_or_update "wf/web-platform/web-platform-enghub-docs"

# Risk
clone_or_update "developer-experience/enghub-happy-paths/work-with-tech-risk"

echo "Done. Repos in: $ENGHUB_DIR"
