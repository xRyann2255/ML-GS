---
created: 2026-04-06
updated: 2026-04-20
tags: [slang, scriptreview, secexpr, tooling, review-refresh]
status: active
relates:
  - slang/lint-edit.md
  - slang/best-practices.md
  - slang/run.md
---

# ScriptReview — Create/Refresh + Validate

## 1) Refresh Diffs (fixes stale review)

```powershell
PYTHON skills/SLANG_REVIEW/src/review.py --db "~{kerberos}!clean" --scripts "_LIB Foo" --review "Review YYYYMMDD 6010-...S*"
```

`--metadata-only` updates fields but does NOT refresh diffs.

## 2) Validate

```powershell
PYTHON skills/SLANG_REVIEW_INSPECT/src/inspect.py --db "~{kerberos}!clean" --source "~{kerberos}!clean;!NYC_EqVol_Source;PS" --review "Review YYYYMMDD 6010-...S*" --no-browser
```

Expected: `INSPECT_LOAD_FAILED=0`, `LATEST_VERSION=<n>` (increments on refresh), `SCRIPT_CVS_REV` matches current.

## 3) Verify Delta Shame (MANDATORY)

Open review URL in browser. Delta shame MUST be zero. Fix issues + refresh until zero.

URL: `https://www.epssp.site.gs.com/ssps/ProdSource/ScriptReview?Name=Review+...`
Unsubmitted: `https://www.epssp.site.gs.com/ssps/ProdSource/MyScriptReviews#unsubmitted-reviews`

## Pre-Create: Check Open Reviews (MANDATORY)

Before creating a NEW ScriptReview, check for existing open reviews whose script list intersects with the scripts you're about to submit:

1. Fetch the user's open reviews from:
   - Unsubmitted: `https://www.epssp.site.gs.com/ssps/ProdSource/MyScriptReviews#unsubmitted-reviews`
   - Submitted: `https://www.epssp.site.gs.com/ssps/ProdSource/MyScriptReviews#submitted-reviews`
2. For each open review, check if any of its scripts overlap with the current script list.
3. If an intersecting review exists → **refresh** it (`--review`) instead of creating a new one. Update metadata (subject, description, testing-description) as needed via `--metadata-only` or a full refresh.
4. Only create a brand-new review if no open review shares any scripts.

This prevents duplicate reviews for the same scripts across sessions.

## Subject (Title) Naming Convention

- Keep it **short, plain-English, and self-explanatory** — anyone reviewing it should understand what changed at a glance.
- Summarize the *what* (e.g. `Fix RegTest stub key for Get PNL`, `Add S3 upload to ETI monitor`).
- **NEVER** include internal process jargon: cure round numbers (`R5`, `R11`), systemic version tags (`4.7`), sprint IDs, or similar identifiers only meaningful to the author. Put those in `--description` or `--driver-for-change`.

## Driver-for-Change Convention

When the user says the driver for change is **"requested by {kerberos}"** (e.g., "requested by villhu"), always format the `--driver-for-change` field as:

```
"Requested by [[yams:{kerberos}]]"
```

The `[[yams:...]]` syntax creates a clickable link to the person's YAMS profile in the ScriptReview UI. Never pass the raw kerberos — always wrap it in `[[yams:...]]`.

## Show Review Link (MANDATORY)

After creating or refreshing a ScriptReview, ALWAYS show the `BROWSER_URL` to the user. Never silently complete a review operation without displaying the clickable link.

## Gotchas

- `secexpr` concatenates Print output — use `Chr(10)` in markers
- `Script Review::Load Review` may return error-ish but still have `ContainerName`
- `secexpr` stderr is noisy — trust marker block + exit code
- **testing-description**: Keep it simple ASCII — no parentheses `()`, no `:=`, no colons `:`. These cause Slang `SL_QUOTED_STRING` parsing errors inside the generated expression. Good: `"Lint pass 0 S1 0 S2. FasTest 6 passed 0 failed 0 errors."` Bad: `"FasTest: 6 passed (0 failed). Fixed Structure() syntax."`
- **Timeout**: Use `--timeout 600` for reviews with 3+ scripts. Default 300s is often insufficient — secexpr takes ~120-130s for 3 scripts and may exceed 300s under load.
- **NEVER run `Get-Process secexpr | Stop-Process -Force`** — this kills secexpr from ALL VS Code sessions, crashing other windows with REPL code=255. If a prior run hung, only kill by specific PID. The Python scripts (review.py, lint.py) already handle their own subprocess timeouts.
- **`--run-mode` is NOT a valid review.py argument.** review.py does NOT accept `--run-mode scratch`. Only `--review` (refresh existing) or omit for new review. Check `--help` before guessing flags.
- **review_compact.py workaround**: When review.py's generated Slang expression exceeds 4096 bytes (common with 5+ scripts), use `workspace/tmp/review_compact.py` — a standalone tool that builds a stripped-down expression without verbose debug `Print` markers. Regenerate it for each review by adapting the script list and review name.
- **`--create` overlays break review**: Scripts created with `edit.py --create` lack CVS metadata. `Generate Diff Datum Structure` calls `@CVS::Script FileName` which throws "Script is not under CVS" for these. For existing production scripts, always use `--rewrite --from-prod` (preserves CVS rev). See `slang/lint-edit.md` for overlay types.
- **ScriptReview objects live in CoreData RW**, not in user DBs. `NameLookup` in the user DB will not find them. Use the web UI (`MyScriptReviews`) to list open reviews.

