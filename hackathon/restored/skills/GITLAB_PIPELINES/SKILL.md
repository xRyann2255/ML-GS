---
name: GITLAB_PIPELINES
description: Authenticate to internal GitLab via SSO and inspect pipelines, jobs, runners, CI config
---

# GITLAB_PIPELINES — GitLab Pipeline Inspection

> **Purpose:** Authenticate to internal GitLab via SSO/SAML and inspect pipelines, jobs, runners, and CI configuration.

**Out of scope:** Creating or modifying pipelines, triggering CI jobs, or managing GitLab project settings.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `GITLAB_PIPELINES` |
| **Scope** | GitLab SSO auth + read-only pipeline/job/runner inspection |
| **Inputs** | Project ID/path, pipeline ID, job ID |
| **Outputs** | JSON/text artifacts in `workspace/tmp/` |
| **Authority** | Read-only (SAML/Kerberos auth) |

## When to Use

- Diagnose failing CI pipelines or jobs.
- Inspect runner tags and availability.
- Validate CI YAML configuration.
- Fetch job logs for analysis.

---

Authenticate to internal GitLab via SSO and inspect pipelines, jobs, runners, CI config.

## Prerequisites

- **Kerberos ticket** — `klist`; if expired, `kdestroy && kinit`
- **GitLab PAT** — stored in Windows Credential Manager (via `git credential approve`)
- **Memory:** `memory/_dormant/ref/gssso-auth.md` (SSO auth flow), `memory/ref/git-workflow.md` (MR conventions)

**Base URL**: `https://gitlab.aws.site.gs.com`

## Authentication

Uses PAT (Personal Access Token) retrieved from Windows Credential Manager via `git credential fill`. The PAT is stored once and used for all GitLab API calls — no SAML/SSO flow needed.

The shared module `skills/_shared/gitlab_auth.py` provides:
- `get_gitlab_pat()` — retrieves PAT from credential store
- `get_gitlab_headers()` — returns `{"PRIVATE-TOKEN": pat}` headers
- `gitlab_api()` — makes authenticated API requests with timeout

## API Endpoints

All calls use PAT headers via `gitlab_api()`. Most need numeric **project ID**:
```
GET /api/v4/projects/<url-encoded-path>
```

### Key Endpoints

| Endpoint | Returns |
| --- | --- |
| `/api/v4/projects/{id}/merge_requests?state=opened` | MRs (iid, title, head_pipeline) |
| `/api/v4/projects/{id}/pipelines/{pid}` | Pipeline (status, ref, sha) |
| `/api/v4/projects/{id}/pipelines/{pid}/jobs` | Jobs list |
| `/api/v4/projects/{id}/jobs/{jid}/trace` | Job log (plain text) |
| `POST /api/v4/projects/{id}/ci/lint` body: `{"content":"<yaml>"}` | Validate CI YAML |
| `/{path}/-/settings/ci_cd?expand_runners=true` | Runner tags (HTML parse) |

### Runner Tags

| Tag | Type | Notes |
| --- | --- | --- |
| `conduit-builder` | Kubernetes | Stable, many replicas. Requires `image:` |
| `pure-linux7` | Bare metal/VM | Less common |
| `cdp-powerplatform-win` | Windows | Windows builds |

## Diagnosing Pipeline Failures

1. Get MR → `head_pipeline.id`
2. Get pipeline jobs → find `status: "failed"`
3. Check `failure_reason`: `runner_system_failure` (infra), `script_failure` (your code), `stuck_or_timeout_failure`
4. Get job trace for details
5. Check `yaml_errors` on pipeline object

| Problem | Fix |
| --- | --- |
| `runner_system_failure` (repeated) | Add `tags: [conduit-builder]` + `retry: {max: 2, when: [runner_system_failure]}` |
| YAML parse error with `: ` | Quote scalars: `- 'echo "Foo: bar"'` |
| Job stuck pending | Verify runner tags match available runners |
| Image pull failure | Verify image name/tag; use `busybox:1.36.1` for docs-only |

## Minimal Docs-Only Pipeline

```yaml
image: busybox:1.36.1
stages: [ci]
docs-only:
  stage: ci
  tags: [conduit-builder]
  script: ['echo "Docs-only: no build/test."']
  interruptible: true
  retry: {max: 2, when: [runner_system_failure]}
  timeout: 1m
```

## Output

Artifacts saved to `workspace/tmp/`: `gitlab-pipeline-{id}-jobs.json`, `gitlab-job-{id}-trace.txt`, `gitlab-runners-settings.html`, `gitlab-ci-lint-result.json`

## Troubleshooting

| Problem | Fix |
| --- | --- |
| 302 redirect loop | Kerberos expired → `kdestroy; kinit` |
| SAML form not found | Redirect chain changed; inspect `$r2.Content` |
| Pipeline JSON 401/404 | Session cookie missing/expired; re-authenticate |
| CI lint valid but pipeline fails | Lint doesn't check runner/image availability |

## Task-Based Execution

**Task label:** `gitlab-pipelines` | **Args file:** `workspace/tmp/gitlab_pipelines_args.json`

Preferred. Write args JSON, then `run_task("gitlab-pipelines")`. Args JSON keys: `project_id` (required), `pipeline_id`, `ref`, `include_trace`, `out_dir`.

## Links

- memory/_dormant/ref/gssso-auth.md — SSO auth flow
- memory/ref/git-workflow.md — MR conventions
