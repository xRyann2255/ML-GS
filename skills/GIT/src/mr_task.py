"""GitLab MR create/update via REST API.

Called by mr_task.cmd — never directly.

Usage: mr_task.py --args-file path/to/args.json

Args JSON (create):
  {
    "action": "create",
    "source_branch": "chore/my-branch",
    "target_branch": "master",
    "title": "Add feature X",
    "description": "## Changes\\n- Did X",
    "out_file": "workspace/tmp/mr_out.txt"
  }

Args JSON (update):
  {
    "action": "update",
    "mr_iid": 70,
    "title": "Updated title",
    "description": "## Changes\\n- Updated",
    "out_file": "workspace/tmp/mr_out.txt"
  }
"""

import argparse
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
from gitlab_auth import get_gitlab_headers, gitlab_api  # noqa: E402

PROJECT_PATH = "eq-tech/sts/ml-vol-estimator"
PROJECT_ID = urllib.parse.quote(PROJECT_PATH, safe="")


def main():
    parser = argparse.ArgumentParser(description="GitLab MR create/update")
    parser.add_argument("--args-file", required=True, help="Path to args JSON file")
    args = parser.parse_args()

    with open(args.args_file, encoding="utf-8") as f:
        a = json.load(f)

    headers = get_gitlab_headers()

    # Get current user
    me = gitlab_api("/user", headers=headers)
    my_id = me["id"]

    action = a.get("action", "create")
    target_branch = a.get("target_branch", "master")
    out_file = a.get("out_file")
    result = ""

    if action == "create":
        source_branch = a.get("source_branch")
        if not source_branch:
            print("ERROR: source_branch is required for create", file=sys.stderr)
            sys.exit(1)
        if not a.get("title"):
            print("ERROR: title is required", file=sys.stderr)
            sys.exit(1)

        # Check if MR already exists
        existing = gitlab_api(
            f"/projects/{PROJECT_ID}/merge_requests"
            f"?state=opened&source_branch={urllib.parse.quote(source_branch, safe='')}",
            headers=headers,
        )
        if existing:
            result = f"MR already exists: !{existing[0]['iid']} - {existing[0]['web_url']}"
            print(result)
            if out_file:
                _write(out_file, result)
            sys.exit(0)

        body = {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": a["title"],
            "description": a.get("description", ""),
            "assignee_id": my_id,
            "remove_source_branch": True,
        }
        mr = gitlab_api(f"/projects/{PROJECT_ID}/merge_requests",
                        method="POST", body=body, headers=headers)
        result = f"MR created: !{mr['iid']} - {mr['web_url']}"

    elif action == "update":
        mr_iid = a.get("mr_iid")
        if not mr_iid:
            print("ERROR: mr_iid is required for update", file=sys.stderr)
            sys.exit(1)

        # Validate MR is still open
        existing_mr = gitlab_api(
            f"/projects/{PROJECT_ID}/merge_requests/{mr_iid}",
            headers=headers,
        )
        mr_state = existing_mr.get("state", "unknown")
        if mr_state != "opened":
            result = f"ERROR: MR !{mr_iid} is '{mr_state}' (not open). Cannot update a {mr_state} MR."
            print(result, file=sys.stderr)
            if out_file:
                _write(out_file, result)
            sys.exit(1)

        body = {
            "assignee_id": my_id,
            "remove_source_branch": True,
        }
        if a.get("title"):
            body["title"] = a["title"]
        if a.get("description"):
            body["description"] = a["description"]

        mr = gitlab_api(f"/projects/{PROJECT_ID}/merge_requests/{mr_iid}",
                        method="PUT", body=body, headers=headers)
        result = f"MR updated: !{mr['iid']} - {mr['web_url']}"

    else:
        print(f"ERROR: Unknown action: {action} (expected 'create' or 'update')",
              file=sys.stderr)
        sys.exit(1)

    print(result)
    if out_file:
        _write(out_file, result)


def _write(path, text):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
