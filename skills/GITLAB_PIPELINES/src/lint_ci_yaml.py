"""Validate a .gitlab-ci.yml file via the GitLab CI Lint API.

Usage: lint_ci_yaml.py --args-file path/to/args.json

Args JSON:
  { "project_id": 117719, "yaml_path": "" }
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
from gitlab_auth import get_gitlab_headers, gitlab_api, GITLAB_BASE  # noqa: E402


def lint_yaml(project_id, yaml_path="", gitlab_base=GITLAB_BASE):
    headers = get_gitlab_headers()

    # Resolve YAML path
    if not yaml_path:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                  "..", "..", ".."))
        yaml_path = os.path.join(repo_root, ".gitlab-ci.yml")

    if not os.path.isfile(yaml_path):
        print(f"ERROR: YAML file not found: {yaml_path}", file=sys.stderr)
        sys.exit(1)

    with open(yaml_path, encoding="utf-8") as f:
        yaml_content = f.read()

    # Lint via API
    result = gitlab_api(f"/projects/{project_id}/ci/lint",
                        method="POST",
                        body={"content": yaml_content},
                        headers=headers,
                        base=gitlab_base)

    if result.get("valid"):
        print("VALID")
    else:
        print("INVALID")

    for e in result.get("errors", []):
        print(f"  ERROR: {e}")

    for w in result.get("warnings", []):
        print(f"  WARNING: {w}")

    # Save result
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                              "..", "..", ".."))
    out_dir = os.path.join(repo_root, "workspace", "tmp")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "gitlab-ci-lint-result.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out_file}")

    return result


def main():
    parser = argparse.ArgumentParser(description="GitLab CI YAML Lint")
    parser.add_argument("--args-file", required=True)
    args = parser.parse_args()

    with open(args.args_file, encoding="utf-8") as f:
        a = json.load(f)

    lint_yaml(
        project_id=int(a["project_id"]),
        yaml_path=a.get("yaml_path", "") or "",
        gitlab_base=a.get("gitlab_base", GITLAB_BASE) or GITLAB_BASE,
    )


if __name__ == "__main__":
    main()
