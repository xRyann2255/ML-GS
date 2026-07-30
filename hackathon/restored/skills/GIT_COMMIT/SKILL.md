---
name: GIT_COMMIT
description: Auto-group changed files by concern and commit with conventional messages in a single task invocation
---

# GIT_COMMIT — Auto-group & Commit

> **Purpose:** Analyze dirty working tree, group files by logical concern, generate conventional commit messages matching repo style, and execute all commits + push in one task invocation (one Allow press).

**Out of scope:** MR creation (use GIT skill's `mr_task`), rebase/conflict resolution (use GIT skill), credential management.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `GIT_COMMIT` |
| **Scope** | Auto-group staged/unstaged/untracked files and commit by concern |
| **Inputs** | JSON args file with optional overrides |
| **Outputs** | Commit summary (console + optional file) |
| **Authority** | Utility — called after implementation work completes |

## When to Use

- After completing a feature, fix, or chore that touched multiple files
- When you want proper conventional commits without manual staging
- When multiple concerns were addressed in one session and need separate commits
- Always prefer this over manually chaining `git add` + `git commit` via the GIT skill

## When NOT to Use

- Rebase/conflict resolution (use GIT skill)
- MR creation (use `gitlab-mr` task)
- When you need to amend or rewrite history (not supported — use GIT skill)

## Args File Format

Write to the fixed path `workspace/tmp/git_commit_args.json` (this is the literal `--args-file` value in the `git-commit` task definition — see `ml-vol-estimator.code-workspace`). The args file path is fixed per task — two concurrent agents writing it race (last writer wins). Keep `out_file` unique per run (put a `run_id` slug in its name); the args file itself is not collision-safe.

Optional `run_id` field (JSON body, pattern `[a-z0-9-]+`) is used only to uniquify `out_file` (e.g. `workspace/tmp/git_commit_out_{run_id}.txt`).

### Minimal (fully automatic — recommended)

```json
{
  "run_id": "commit-20260707",
  "out_file": "workspace/tmp/git_commit_out_commit-20260707.txt"
}
```

### With agent-supplied overrides

```json
{
  "push": true,
  "branch": "feat/my-branch",
  "dry_run": false,
  "overrides": [
    {
      "files": ["src/volforecast/features/har.py", "tests/test_har.py"],
      "message": "feat(features): improve HAR lag computation"
    }
  ],
  "run_id": "har-commit-20260707",
  "out_file": "workspace/tmp/git_commit_out_har-commit-20260707.txt"
}
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `push` | No | `true` | Push to remote after all commits |
| `branch` | No | current HEAD | Target branch for push |
| `dry_run` | No | `false` | Print plan without executing |
| `overrides` | No | `[]` | Agent-specified groups that bypass auto-detection for those files |
| `run_id` | No | — | Slug (`[a-z0-9-]+`); used only to uniquify `out_file` — the args file itself is fixed. |
| `out_file` | No | — | Path to write execution summary |

## Grouping Rules

Files are grouped by directory path into logical concerns:

| Path pattern | Group | Default prefix |
|---|---|---|
| `src/volforecast/features/` | features | `feat(features):` |
| `src/volforecast/models/` | models | `feat(models):` |
| `src/volforecast/evaluation/` | evaluation | `feat(eval):` |
| `src/volforecast/pipeline/` | pipeline | `feat(pipeline):` |
| `src/volforecast/cli/` | cli | `feat(cli):` |
| `src/volforecast/data/` | data | `feat(data):` |
| `src/volforecast/utils/` | utils | `chore(utils):` |
| `src/volforecast/` (other) | src | `feat(src):` |
| `tests/` | tests | `test:` |
| `memory/` | memory | `docs(memory):` |
| `workspace/research/` | research | `docs(research):` |
| `workspace/configs/` | config | `chore(config):` |
| `workspace/docs/` | docs | `docs:` |
| `skills/` | skills | `feat(skills):` |
| `policy/`, `workflows/`, `personas/` | framework | `chore(framework):` |
| `.github/` | ci | `chore(ci):` |
| `data/` (top-level) | data-files | `chore(data):` |
| Everything else | misc | `chore:` |

**Type override logic:** The default prefix above assumes new files. For modification-only groups:
- Code files → `fix(scope):` or `refactor(scope):` based on diff size
- Docs/memory → `docs(scope): update ...`
- Config → `chore(scope): update ...`

## Message Generation Style

Messages match the existing repo style (from git log):

```
feat: implement data pipeline - Chunk Store access, tick resampling, daily RV
feat(src): scaffold Python package skeleton and ML workflow prompts
fix(memory): patch research card gaps
refactor: simplify agentic workflow framework
chore: transformation cleanup — memory, skills, docs, workspace updates
test: repository access permissions
docs: rewrite AGENTS.md for ML vol forecasting
```

Rules:
1. Start with lowercase action verb (implement, add, fix, update, refactor, clean up)
2. Be specific about WHAT was done — name the actual things
3. List 2-3 items after a dash or comma when appropriate
4. Max 72 characters
5. Never generic ("update files", "make changes", "various fixes")

## Denied Paths (never staged)

- `workspace/docs/enghub/` — embedded git repo
- `workspace/tmp/` — ephemeral files
- `__pycache__/` — Python bytecode
- `*.pyc` — compiled Python
- `.git/` — git internals

## Execution Flow

```
Agent writes args JSON → run_task("git-commit") → [ONE ALLOW] →
  Script internally:
    1. git status --porcelain
    2. Filter denied paths
    3. Group files by concern (path heuristics)
    4. Apply overrides (if any)
    5. For each group:
       a. git add <file1> <file2> ...
       b. Generate commit message from file context
       c. git commit -m "type(scope): description"
    6. git push origin <branch> (if push=true)
  → Writes summary to out_file
Agent reads out_file
```

## Task Execution

```
run_task("git-commit", workspaceFolder: "h:\ml-vol-estimator")
```

The task reads from the args file path specified in the workspace task definition.

## Example Output

```
=== GIT_COMMIT: 3 commits planned ===

[1/3] feat(features): implement noise-robust estimators - RK, TSRV, pre-averaged RV
  → src/volforecast/features/noise_robust.py (new)
  → src/volforecast/features/transforms.py (modified)

[2/3] test: add noise-robust estimator test coverage
  → tests/test_noise_robust.py (new)

[3/3] docs(research): update feature engineering status and open questions
  → workspace/research/feature-engineering-status.md (modified)
  → workspace/research/open-questions.md (modified)

=== Executing ===
[1/3] ✓ committed (abc1234)
[2/3] ✓ committed (def5678)
[3/3] ✓ committed (9ab0cde)
Push → origin/feat/noise-robust ✓

Done: 3 commits, 5 files, pushed to feat/noise-robust
```

## Conventions

- See `memory/ref/git-workflow.md` for branch naming and commit conventions
- NEVER stages files matching denied paths
- NEVER uses `git add -A` (stages files explicitly per-group)
- NEVER pushes to `master` directly
- Commits are ordered: source code first, tests second, docs/config last

## Links

- memory/ref/git-workflow.md — branch naming, MR workflow, commit conventions
