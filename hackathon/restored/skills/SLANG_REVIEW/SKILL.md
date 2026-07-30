---
name: SLANG_REVIEW
description: Create or update ScriptReview code reviews for Slang changes
---

# SLANG_REVIEW — Create ScriptReview Code Reviews

> **Purpose:** Create or update code reviews via the `ScriptReview` API. Supports CVSed and uncvsed scripts, manages review metadata and diff refreshes.
> **Out of scope:** approving reviews, merging, lint/tests.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `SLANG_REVIEW` |
| **Scope** | Create/update ScriptReview code reviews |
| **Inputs** | Script names, DB path, subject, description |
| **Outputs** | Review URL, confirmation of create/update |
| **Authority** | Write (secexpr --safe) |

## When to Use

- Submit or update Slang script code reviews after completing lint and test gates.

> **Memory:** `memory/_dormant/slang/review.md` (shame check, CVSed/uncvsed conventions, delta shame workflow).

> **Python:** Resolve `PYTHON` via the PYTHON_PATH skill before running commands below.

## How to Use

### Pre-Create Check (MANDATORY)

Before creating a new review, check for existing open reviews with overlapping scripts:
1. Open the MyScriptReviews web page and check both tabs:
   - Unsubmitted: `https://www.epssp.site.gs.com/ssps/ProdSource/MyScriptReviews#unsubmitted-reviews`
   - Submitted: `https://www.epssp.site.gs.com/ssps/ProdSource/MyScriptReviews#submitted-reviews`
   - Note: `MyScriptReviews` is a **web page**, not a Slang variable. ScriptReview objects live in CoreData RW, not in user DBs.
2. If any open review contains scripts that overlap with the current `--scripts` list, use `--review` (refresh) on the existing review instead of creating a new one.
3. Only create a brand-new review when no open review shares any scripts.

### Create

```cmd
PYTHON skills/SLANG_REVIEW/src/review.py ^
    --db "~{kerberos}!clean" ^
    --scripts "_LIB Foo" "Test: Foo" ^
    --subject "Subject" --description "What changed" ^
    --driver-for-change "Why" ^
    --testing-description "RegTest passes" ^
    > workspace/tmp/review_output.txt 2>&1
```

### Update Existing Review

```cmd
PYTHON skills/SLANG_REVIEW/src/review.py ^
    --db "~{kerberos}!clean" ^
    --scripts "_LIB Foo" "Test: Foo" ^
    --review "Review 20260331 6010-2204722S*" ^
    --testing-description "Updated notes" ^
    > workspace/tmp/review_update_output.txt 2>&1
```

- `--scripts` is **always required** — pass the full list of scripts for both create and refresh.
- When `--review` is provided, refreshes script diffs (creates new review version).
- `--metadata-only` with `--review`: updates fields only (no diff refresh).
- After success, runs `SLANG_REVIEW_INSPECT` for validation (shame, test headers, etc.).

### Arguments

| Argument | Req | Description |
| --- | --- | --- |
| `--db` | Yes | SecDB database path |
| `--scripts` | Yes | Script names (always required — full list for both create and refresh) |
| `--review` | No | Existing review name — if provided, refresh it; otherwise create new |
| `--subject` | Create | Mail subject / title (required on create) — see naming rules below |
| `--description` | Create | Description of changes (required on create) |
| `--driver-for-change` | Create | Main driver (required on create) |
| `--testing-description` | No | How changes were tested |
| `--source` | No | secexpr `--source` override |
| `--metadata-only` | No | With `--review`: update fields only, skip diff refresh |

### Subject Naming Convention

- Keep it **short, plain-English, and self-explanatory** — anyone on the team should understand it at a glance.
- Summarize *what changed* (e.g. `Fix RegTest stub key for Get PNL`, `Add S3 upload to ETI monitor`).
- **NEVER** include internal process jargon: cure round numbers (`R5`, `R11`), systemic version tags (`4.7`), sprint IDs, or similar. Those belong in `--description` or `--driver-for-change`.

### User Config

Per-user config at `workspace/config/user.json` (gitignored):
```powershell
cp workspace/config/user.json.template workspace/config/user.json
```
```json
{ "review": { "auto_submit": false, "auto_commit": false, "auto_push": false } }
```
Missing file defaults: `auto_submit=false`, `auto_commit=true`, `auto_push=true`.

### Output

```
REVIEW_URL=Review 20260331 6010-2204637S*
BROWSER_URL=https://...
REFRESH_OLD_VERSION=<n>   # only for --review refresh
REFRESH_NEW_VERSION=<n>
```

Logs/artifacts: `workspace/tmp/slang_review_logs/`

## Key API Reference

See memory/_dormant/slang/review-api.md for function signatures (`Generate Diff Datum Structure`, `Create Review`, `Edit Params`, `Load Review`), update patterns, required links, script classification, and troubleshooting.

## Task-Based Execution (Zero Allow — Preferred)

Use `run_task("slang-review")` instead of `run_in_terminal` to avoid the Copilot "Allow" prompt. **The entire workflow uses zero terminal calls.**

### Workflow

### Concurrency-Safe Workflow

Multiple VS Code windows may run reviews concurrently on the same workspace. To avoid
file collisions, **always include `run_id` in the args filename and let the script
derive a unique results filename automatically.**

1. **Write args file** to the fixed path `workspace/tmp/review_args.json` (this is the literal `--args-file` value in the `slang-review` task definition — see `ml-vol-estimator.code-workspace`). Include `run_id` (pattern `[a-z0-9-]+`) inside the body — the script uses it to derive a unique results filename. Use `create_file` (no terminal):

```json
// workspace/tmp/review_args.json
{
  "db": "~{kerberos}!{sub_db}",
  "scripts": ["_LIB Foo", "Test: Foo"],
  "subject": "Subject of the review change",
  "description": "Description of what changed and why",
  "driver_for_change": "Reason the change is needed",
  "testing_description": "RegTest passes, lint 0 S1 0 S2",
  "run_id": "smm-metrics-20260429"
}
```

For refresh, add `"review": "Review 20260331 6010-2204722S*"`.
For metadata-only, add `"metadata_only": true` with `"review"`.

Generate `run_id` as a short descriptive slug matching `[a-z0-9-]+` (e.g. `smm-metrics-20260429`).
The args file path is fixed per task — two concurrent agents writing it race (last writer wins). Result files stay collision-free because the script auto-derives `slang_review_results_{run_id}.json` from the `run_id` field.

2. **Launch via the predefined task** (no Allow):

```
run_task("slang-review")
```

The task reads `workspace/tmp/review_args.json` (fixed path in the task definition).

3. **Read results** from `workspace/tmp/slang_review_results_{run_id}.json`:
   - On launch, review.py writes `{"status": "running", "run_id": "..."}`.
   - On completion, review.py overwrites with `{"status": "done", "run_id": "...", "gate": "...", ...}`.
   - `run_task` blocks until done — no polling needed.

```json
{
  "status": "done",
  "run_id": "<unique-id>",
  "gate": "PASS",
  "mode": "create",
  "review_name": "Review 20260420 6010-2204722S*",
  "review_url": "https://...",
  "scripts": ["_LIB Foo", "Test: Foo"]
}
```

4. **Evaluate gate**: `gate == "PASS"` → review created/refreshed. `gate == "FAIL"` → check `diagnostics` array and `safe_mode` flag.

### CRITICAL: No `run_in_terminal` anywhere

| Step | Tool | Allow? |
|---|---|---|
| Write args JSON | `create_file` | No |
| Launch task | `run_task` | No |
| Poll results | `read_file` | No |
| Read results | `read_file` | No |

Do NOT use `run_in_terminal` to delete old results, poll, or check — all of those trigger Allow prompts.

### Args File Keys

| Key | Type | Description |
|---|---|---|
| `db` | string | SecDB database path (e.g. `~jdoe!commit`) |
| `scripts` | string[] | Script names (full list, always required) |
| `review` | string | Existing review name (refresh mode; omit for create) |
| `subject` | string | Mail subject / title (required on create) |
| `description` | string | Change description (required on create) |
| `driver_for_change` | string | Driver for change (required on create) |
| `testing_description` | string | Testing notes (optional) |
| `metadata_only` | bool | Update metadata only, skip diff refresh (optional) |
| `source` | string | Source chain override (optional) |
| `timeout` | int | Timeout in seconds (optional, default 300) |
| `output_json` | string | Custom output path (optional) |
| `run_id` | string | Slug (`[a-z0-9-]+`); lives inside the JSON body; used to derive the unique results filename `slang_review_results_{run_id}.json`. |

### Result JSON Structure

```json
{
  "status": "done",
  "run_id": "<unique-id>",
  "debug_id": "20260420_143000",
  "mode": "create",
  "scripts": ["_LIB Foo", "Test: Foo"],
  "gate": "PASS",
  "review_name": "Review 20260420 6010-2204722S*",
  "review_url": "https://..."
}
```

On failure:
```json
{
  "status": "done",
  "run_id": "<unique-id>",
  "gate": "FAIL",
  "safe_mode": false,
  "diagnostics": ["DIFFS_ERROR=..."]
}
```

### Notes

- **`review_task.cmd`** auto-detects Python from `H:\venv*` (highest version first).
- **Default output**: `workspace/tmp/slang_review_results.json` (or `slang_review_results_{run_id}.json` when `run_id` is set in the body).
- **Sentinel mechanism**: File starts with `{"status": "running", "run_id": "..."}`,
  then gets overwritten with `{"status": "done", "run_id": "...", ...}` on completion.
- **`run_id` freshness**: Always set a unique `run_id` (pattern `[a-z0-9-]+`) inside the JSON body so the script writes to a fresh `slang_review_results_{run_id}.json` and no other agent's stale result is read by mistake.
- **`run_task` blocks until the task process exits** (vscode-tasks.md E7) — no polling loops required; read the results file the moment `run_task` returns.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Review creation times out | Raise `timeout` in the args body; verify `run_id` is set so the results filename is unique |
| Stale result read | Set a fresh `run_id` per operation (pattern `[a-z0-9-]+`) |

## Links

- memory/_dormant/slang/review.md — shame check, CVSed/uncvsed conventions
- memory/_dormant/slang/review-api.md — API signatures, troubleshooting
