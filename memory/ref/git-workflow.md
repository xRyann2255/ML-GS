---
created: 2026-04-08
updated: 2026-04-09
tags: [git, gitlab, merge-request, push, commit, workflow]
status: active
relates:
  - ref/devtools.md
---

# Git Workflow — ml-vol-estimator

## Repository

- Remote: `https://gitlab.aws.site.gs.com/eq-tech/sts/ml-vol-estimator`
- Local: `H:\ml-vol-estimator`
- `master` (protected, default) — push via MR only.
- **NEVER use `main` as a working branch.** Always create feature branches: `feat/<topic>`, `fix/<topic>`, `chore/<topic>`.

## Credentials

Windows Credential Manager. Retrieve programmatically:
```powershell
$cred = echo "protocol=https`nhost=gitlab.aws.site.gs.com" | git credential fill 2>$null
$token = ($cred | Select-String "password" | ForEach-Object { ($_ -split '=',2)[1] })
```

## Workflow

1. **Stage explicitly** — NEVER `git add -A` (embedded repo at `workspace/docs/enghub/cicd-platform-docs`)
2. **Rebase onto origin/master** — `git fetch origin master; git rebase origin/master`. This is **MANDATORY** before pushing for an MR. The feature branch must be cleanly ahead of `origin/master` — never push without rebasing first. Use `--force-with-lease` if the branch was already pushed.
3. **Commit** — `git commit -m "Subject\n\n- detail"`
4. **Push** — `git push origin feat/<topic>`. If the remote branch was deleted (after previous MR merge with `remove_source_branch`), first `git remote prune origin` then push (creates new branch). NEVER push to `master` — protected.
5. **Create MR** — POST `/api/v4/projects/{id}/merge_requests`. MANDATORY fields: `title`, `description`, `assignee_id` (from `/api/v4/user`), `remove_source_branch=true`, `source_branch=feat/<topic>`, `target_branch=master`
6. **Update MR** — PUT `.../merge_requests/{iid}`. Same mandatory fields: `title`, `description`, `assignee_id`, `remove_source_branch`
7. **Always show the MR URL** — after ANY MR operation (create, update, push), print the full `web_url` so the user can review it. This is mandatory — never silently create or update an MR without surfacing the link.

### MR Title & Description Convention

- **Title:** Keep it short, generic, and human-readable — summarize the *what*, not the *how*. NEVER mention internal jargon like cure round numbers (R5, R11), systemic version numbers (4.7), or any internal process identifiers. The title must be understandable by anyone on the team at a glance. Good: `Fix persona fields and policy routing`, `Add Brazil ETI monitoring`. Bad: `Cure R11 + systemic 4.7 remediation`, `Cure R7: fix support.md registration`.
- **Description:** Put the detailed breakdown here — specific files changed, bugs fixed, technical context, ticket/cure references, internal process identifiers, etc. Cure rounds and systemic versions belong here, not in the title.

### MR API Template

```powershell
$projectId = [uri]::EscapeDataString("eq-tech/sts/ml-vol-estimator")
$headers = @{ "PRIVATE-TOKEN" = $token; "Content-Type" = "application/json" }
$me = Invoke-RestMethod -Uri "https://gitlab.aws.site.gs.com/api/v4/user" -Headers $headers
$body = @{ source_branch="feat/<topic>"; target_branch="master"; title="..."; description="..."; assignee_id=$me.id; remove_source_branch=$true } | ConvertTo-Json -Compress
# Create: Post .../merge_requests  |  Update: Put .../merge_requests/$mrIid
```

## Pitfalls

- Never `git add -A` — embedded repo gets staged
- Never push to `master` directly — protected
- **NEVER use `git commit --amend`** — always create new commits. Keep history linear and explicit.
- **NEVER use `main` as a working branch** — always create `feat/`, `fix/`, or `chore/` branches
- **ALWAYS rebase onto `origin/master`** before pushing — `git fetch origin master; git rebase origin/master`. Without this, the MR will show as needing rebase and can't merge. This is the most common mistake.
- If previous commits were already squash-merged into master, `git rebase --skip` the duplicates
- **Remote `main` deleted after MR merge**: Since `remove_source_branch=true` is always set, after each MR merge the remote `main` is deleted. On next push: `--force-with-lease` will fail with "stale info" and `git fetch origin main` will fail with "couldn't find remote ref". Fix: `git remote prune origin; git push origin main` (creates new remote branch). Always check `git remote show origin` if push fails unexpectedly.
- **Rebase in non-interactive task mode:** The git task wrapper sets `GIT_EDITOR` to `noop_editor.cmd` (a dedicated no-op script) to prevent editor-blocking. `cmd /c exit /b 0` does NOT work as an editor — git's shell eats the `/c` flag. If rebase hits conflicts, the task will fail. **You MUST resolve conflicts yourself** — read the conflicted files, understand BOTH sides (local intent vs upstream changes), and produce a thoughtful merge that incorporates the best of both. Do NOT mechanically pick one side — analyze what each change adds and combine intelligently. Then `git add` the resolved files and `rebase --continue`. NEVER ask the user to resolve conflicts unless they explicitly request manual control. Only abort+force-push if conflicts are genuinely too complex to resolve confidently.
- **Dirty working tree blocks `rebase --continue`:** Even when `git status` says "(all conflicts fixed)", if there are unstaged modified files in the working tree, `rebase --continue` will fail with "You must edit all merge conflicts." The fix: `git stash push <dirty-file>` before running `rebase --continue`, then `git stash pop` after the rebase completes. Use pathspec stash to target only the blocking file. NEVER use `--keep-index` — it stashes the staged resolution too, breaking the rebase state.
- `git stash pop` unstages — re-add before committing
- GitLab HTTP→HTTPS redirect warning is normal
- **NEVER use `git push -o merge_request.create`** — it creates MRs without a description, which violates the mandatory description policy. Always create MRs via the API (`POST /merge_requests`) with both `title` and `description` fields. If an MR already exists, update it via `PUT /merge_requests/{iid}` to add/fix the description.
