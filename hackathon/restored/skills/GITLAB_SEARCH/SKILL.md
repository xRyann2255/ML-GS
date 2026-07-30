---
name: GITLAB_SEARCH
description: Search GitLab code, MRs, commits, issues, and projects via the Search API — global, group, or project scope
---

# GITLAB_SEARCH — GitLab Code & Artifact Search

> **Purpose:** Search internal GitLab for code (blobs), merge requests, commits, issues, and projects. Defaults to global search; optionally scoped to a project or group.

**Out of scope:** Modifying GitLab resources (creating MRs, issues). Use GITLAB_PIPELINES for pipeline inspection.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `GITLAB_SEARCH` |
| **Scope** | Read-only search across GitLab via Search API |
| **Inputs** | Query string, scope (blobs/commits/merge_requests/issues/projects), optional ProjectId/GroupId |
| **Outputs** | Console summary + JSON in `workspace/tmp/gitlab-search-results.json` |
| **Authority** | Read-only (PRIVATE-TOKEN auth) |

## When to Use

- Find code patterns, function usages, or configuration across GitLab repos.
- Search for merge requests by keyword (e.g., feature names, ticket IDs).
- Discover GitLab projects by name or topic.
- Locate commit messages matching a pattern.
- Find issues across projects.

Do **not** use for:
- Slang code search → use **SLANG_GLIMPSE** instead.
- Pipeline/job inspection → use **GITLAB_PIPELINES** instead.
- Creating or modifying GitLab resources.

## Prerequisites

- **GitLab PAT** in Windows Credential Manager (stored via `git credential approve` or interactive `git push`).
- **PowerShell 5.1+**.
- Resolve GitLab base URL at runtime — never hardcode project IDs in automation.

## Procedures

All procedures use the `gitlab-search` VS Code task with `--args-file`. The Python script `src/gitlab_search.py` handles PAT auth, pagination, project path resolution, and result formatting.

### 1. Global Code Search (default)

Search across **all** accessible GitLab projects:

```json
{ "query": "<search term>", "max_results": 20, "out_file": "workspace/tmp/gitlab-search-results.json" }
```

### 2. Project-Scoped Search

Narrow to a single project by numeric ID:

```json
{ "query": "<search term>", "project_id": 117719, "max_results": 20, "out_file": "workspace/tmp/gitlab-search-results.json" }
```

To find a project's numeric ID, search by name first:

```json
{ "query": "<project name>", "scope": "projects", "out_file": "workspace/tmp/gitlab-search-results.json" }
```

### 3. Group-Scoped Search

Narrow to all projects within a GitLab group:

```json
{ "query": "<search term>", "group_id": 4521, "scope": "blobs", "out_file": "workspace/tmp/gitlab-search-results.json" }
```

### 4. Merge Request Search

```json
{ "query": "<keyword>", "scope": "merge_requests", "out_file": "workspace/tmp/gitlab-search-results.json" }
```

### 5. Commit Search

```json
{ "query": "<commit message pattern>", "scope": "commits", "out_file": "workspace/tmp/gitlab-search-results.json" }
```

## Search Scopes

| Scope | Searches | Global | Project | Group |
|-------|----------|--------|---------|-------|
| `blobs` (default) | File content (code) | Yes | Yes | Yes |
| `wiki_blobs` | Wiki content | Yes | Yes | Yes |
| `commits` | Commit messages | Yes | Yes | Yes |
| `merge_requests` | MR titles & descriptions | Yes | Yes | Yes |
| `issues` | Issue titles & descriptions | Yes | Yes | Yes |
| `milestones` | Milestone titles | Yes | Yes | Yes |
| `projects` | Project names & descriptions | Yes | — | — |

## Output

- **Console:** Formatted summary with filenames, paths, line numbers, and content previews.
- **JSON:** Raw results saved to `workspace/tmp/gitlab-search-results.json`.
- Override output path with `-OutFile <path>`.

## Authentication

Uses `PRIVATE-TOKEN` header. Token is retrieved at runtime from Windows Credential Manager via `git credential fill` for the GitLab host. No tokens are stored in code or config.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "No GitLab PAT found" | Run `git push` to any GitLab repo interactively to store credentials, or use `git credential approve` |
| 401 Unauthorized | PAT expired or revoked — regenerate at GitLab → Settings → Access Tokens |
| Empty results on global search | GitLab Advanced Search may not index all projects — try project-scoped search |
| Timeout on large queries | Reduce `-MaxResults` or narrow with `-ProjectId`/`-GroupId` |

## Task-Based Execution (Zero Allow — Preferred)

Use `run_task("gitlab-search")` instead of `run_in_terminal` to avoid the Copilot "Allow" prompt.

### Workflow

1. **Write args file** (use `create_file` — no terminal):

```json
{
  "query": "some_function",
  "scope": "blobs",
  "project_id": 0,
  "group_id": 0,
  "max_results": 20,
  "out_file": "workspace/tmp/gitlab-search-results.json"
}
```

Args file keys: `query` (required), `scope`, `project_id`, `group_id`, `max_results`, `out_file`.

2. **Launch via predefined VS Code Task** (no Allow):

```
run_task("gitlab-search", workspaceFolder: "h:\ml-vol-estimator")
```

The task reads `workspace/tmp/gitlab_search_args.json` automatically.
```

3. **Read results** with `read_file` on `workspace/tmp/gitlab-search-results.json` (no terminal).

### No `run_in_terminal` anywhere

| Step | Tool | Allow? |
|---|---|---|
| Write args JSON | `create_file` | No |
| Launch task | `run_task` | No |
| Read results | `read_file` | No |

## Links

- memory/ref/git-workflow.md — credential retrieval pattern, project info
