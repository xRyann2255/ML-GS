"""Search GitLab code, MRs, commits, and issues via the Search API.

Usage: gitlab_search.py --args-file path/to/args.json

Args JSON keys: query, scope, project_id, group_id, max_results, out_file
"""

import argparse
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
from gitlab_auth import get_gitlab_headers, gitlab_api, GITLAB_BASE  # noqa: E402

VALID_SCOPES = ("blobs", "wiki_blobs", "commits", "merge_requests",
                "issues", "milestones", "projects")


def search(query, scope="blobs", project_id=0, group_id=0,
           max_results=20, gitlab_base=GITLAB_BASE, headers=None):
    """Paginate GitLab search API and return results list."""
    if headers is None:
        headers = get_gitlab_headers()

    if project_id:
        prefix = f"/projects/{project_id}/search"
        scope_label = f"project {project_id}"
    elif group_id:
        prefix = f"/groups/{group_id}/search"
        scope_label = f"group {group_id}"
    else:
        prefix = "/search"
        scope_label = "global"

    all_results = []
    page = 1
    per_page = min(max_results, 100)

    while len(all_results) < max_results:
        encoded = urllib.parse.quote(query, safe="")
        path = f"{prefix}?scope={scope}&search={encoded}&page={page}&per_page={per_page}"
        items = gitlab_api(path, headers=headers, base=gitlab_base)
        if not items:
            break
        all_results.extend(items)
        page += 1
        if len(items) < per_page:
            break

    return all_results[:max_results], scope_label


def resolve_project_paths(results, scope, headers, gitlab_base):
    """Resolve project_id → path_with_namespace for blob/commit results."""
    cache = {}
    if scope not in ("blobs", "wiki_blobs", "commits"):
        return cache
    unique_ids = {r["project_id"] for r in results if r.get("project_id")}
    for pid in unique_ids:
        try:
            proj = gitlab_api(f"/projects/{pid}", headers=headers, base=gitlab_base)
            cache[pid] = proj.get("path_with_namespace")
        except Exception:
            cache[pid] = None
    return cache


def display(results, scope, proj_cache, query, scope_label, gitlab_base):
    """Print results to stdout."""
    print(f"\nFound {len(results)} result(s) for '{query}' "
          f"(scope: {scope}, {scope_label})\n")

    if scope == "blobs":
        for r in results:
            proj_path = proj_cache.get(r.get("project_id"))
            proj = f" [{proj_path}]" if proj_path else (
                f" [project:{r['project_id']}]" if r.get("project_id") else "")
            print(f"  {r.get('filename', '?')}{proj}")
            print(f"    path: {r.get('path', '?')}")
            if proj_path:
                anchor = f"#L{r['startline']}" if r.get("startline") else ""
                print(f"    {gitlab_base}/{proj_path}/-/blob/"
                      f"{r.get('ref', 'main')}/{r.get('path', '')}{anchor}")
            if r.get("startline"):
                line_count = r.get("data", "").count("\n") + 1
                print(f"    lines: {r['startline']}-{r['startline'] + line_count - 1}")
            data = r.get("data", "")
            print(f"    {data[:200]}")
            print()

    elif scope == "merge_requests":
        for r in results:
            print(f"  !{r.get('iid')} [{r.get('state')}] {r.get('title')}")
            author = r.get("author", {}).get("username", "?")
            print(f"    author: {author}  created: {r.get('created_at')}")
            print(f"    {r.get('web_url')}")
            print()

    elif scope == "commits":
        for r in results:
            proj_path = proj_cache.get(r.get("project_id"))
            print(f"  {r.get('short_id', '?')} {r.get('title', '?')}")
            print(f"    author: {r.get('author_name')}  "
                  f"date: {r.get('created_at')}")
            if proj_path and r.get("id"):
                print(f"    {gitlab_base}/{proj_path}/-/commit/{r['id']}")
            print()

    elif scope == "issues":
        for r in results:
            print(f"  #{r.get('iid')} [{r.get('state')}] {r.get('title')}")
            author = r.get("author", {}).get("username", "?")
            print(f"    author: {author}  created: {r.get('created_at')}")
            if r.get("web_url"):
                print(f"    {r['web_url']}")
            print()

    elif scope == "projects":
        for r in results:
            print(f"  {r.get('path_with_namespace')} [id:{r.get('id')}]")
            desc = r.get("description", "")
            if desc:
                print(f"    {desc[:120]}")
            print(f"    {r.get('web_url')}")
            print()

    else:
        print(json.dumps(results, indent=2))


def main():
    parser = argparse.ArgumentParser(description="GitLab Search")
    parser.add_argument("--args-file", required=True)
    args = parser.parse_args()

    with open(args.args_file, encoding="utf-8") as f:
        a = json.load(f)

    query = a["query"]
    scope = a.get("scope", "blobs")
    project_id = int(a.get("project_id", 0) or 0)
    group_id = int(a.get("group_id", 0) or 0)
    max_results = int(a.get("max_results", 20) or 20)
    out_file = a.get("out_file", "")
    gitlab_base = a.get("gitlab_base", GITLAB_BASE)

    if scope not in VALID_SCOPES:
        print(f"ERROR: Invalid scope '{scope}'. "
              f"Valid: {', '.join(VALID_SCOPES)}", file=sys.stderr)
        sys.exit(1)

    headers = get_gitlab_headers()
    results, scope_label = search(query, scope, project_id, group_id,
                                  max_results, gitlab_base, headers)
    proj_cache = resolve_project_paths(results, scope, headers, gitlab_base)
    display(results, scope, proj_cache, query, scope_label, gitlab_base)

    # Save JSON
    if not out_file:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                  "..", "..", ".."))
        out_file = os.path.join(repo_root, "workspace", "tmp",
                                "gitlab-search-results.json")
    d = os.path.dirname(out_file)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Raw JSON saved to {out_file}")


if __name__ == "__main__":
    main()
