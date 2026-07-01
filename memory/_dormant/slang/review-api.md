---
domain: slang
subject: review-api
title: "ScriptReview API — Function Signatures & Troubleshooting"
created: 2026-05-12
updated: 2026-05-12
tags: [slang, scriptreview, api, code-review]
status: active
---

# ScriptReview API Reference

## `ScriptReview::Generate Diff Datum Structure`

From `_LIB Script Review Fns`. Generates diff data for review submission.

| Parameter | Type | Description |
| --- | --- | --- |
| `ScriptPtrs` | `Security List` | Securities to review |
| `Expressions` | `Structure` | Pass `Structure()` if not modifying in SVE buffer |
| `Scripts` | `Array` | `[{| Script Name; Revision1; Revision2 |}]` for CVSed scripts |
| `New Scripts` | `Array` | `[{| Script Name; Directory; FileName |}]` for uncvsed scripts |
| `SourceDb` | `Database` | `SourceDatabase().Left` |

## `ScriptReview::Create Review`

Returns `ScriptReview::Diffs()` with `.ContainerName`.

| Parameter | Type | Description |
| --- | --- | --- |
| `ScriptPtrs` | `Security List` | Securities to review |
| `Scripts` | `Structure` | Output of `Generate Diff Datum Structure` |
| `Display Review Page` | `Double` | `False` to suppress browser |
| `Edit Params` | `ScriptReview::Edit Params` | Review metadata |
| `ReviewName` | `String` | Existing review name (refresh — creates new version) |
| `Skip Tests` | `Double` | `True` to skip (default for refresh) |

## `ScriptReview::Edit Params`

Fields: `Mail Subject`, `Description`, `Driver For Change Stored`, `Testing Description`, `Tested` ("Yes"/"No"), `Change Risk Class` (`CM ChangeRiskClass::Low`, needs `_Const Controls CM`), `Issue Id`

## `Script Review::Load Review`

Params: `ReviewName` (String), `Use RW Db` (Double, `True` for updates), `Refresh` (Double).

## Update Patterns

- **Metadata-only**: `Diffs.Update Review Details(LoginName(), Testing Description := "...")` — no diff refresh
- **Refresh diffs**: `@ScriptReview::Create Review(..., ReviewName := "Review ...")` — new version

`Diffs.Update Review Details` params: `User` (required, `LoginName()`), `Mail Subject`, `Description`, `Driver for Change Stored`, `Testing Description`, `Change Risk Class`, `Expiration Date`, `Issue ID`, `Comment`, `Suppress Notification`. All except `User` default `Null` (unchanged).

Reference pattern: `Private::Submit Review` in `_LIB Revert Script From CVS` (~lines 571-612).

## Required Links

`_LIB Script Review Fns`, `_LIB Script Review Load Fns`, `_LIB HTML Helper Fns`, `_LIB Web Browser Control`, `_LIB Security Fns`, `_LIB CVS Script Functions`, `_LIB CVS Commit Helper Fns`, `_TYPE Script Review Helpers`, `_Const Controls CM`

## Script Classification

CVSed vs uncvsed determined by `@CVS::Script Revision(Script Ptr)`:
- Has revision → `Existing Scripts` array with `Revision1 := Rev, Revision2 := ""`
- No revision → `New Scripts` array with `Directory` + `FileName` from `@CVS::Get Slang Auto Dir FilePath()`; fallback `Directory := "secdb_scripts"`, `FileName := Script Name`

## Troubleshooting

| Error | Fix |
| --- | --- |
| `Filename may not begin with a /` | Uncvsed script empty Dir/File → `Directory := "secdb_scripts"` |
| `Expected to be uncvsed script` | CVSed script in `New Scripts` → check `@CVS::Script Revision()` |
| `SubDbDrvGetByName: Object not found` | Script doesn't exist in database |
| `unexpected SL_SYMBOL` parse error | `--` as comment → use `//` |
| File lock on output | Use `read_file` or `Get-Content` instead of `ReadAllLines` |
| secexpr truncates output silently | Line >4096 chars in stdin (inherent buffer limit, not caused by `-t`). review.py validates line lengths and raises `ValueError` if exceeded. Shorten `--testing-description` or reduce script count. |
| `Access of an uninitialized variable` in review expression | secexpr stdin evaluates each line independently. Variables in `Try`/`If` blocks on one line NOT visible on other lines. Use top-level statements (which persist across evaluations). |
| Massive stderr (50K+ lines) | Expected 3001 noise from CoreData session. review.py redirects stderr to file. If running manually, use `2>nul` or `2>stderr.txt`. The `-t` flag (trace errors) amplifies this — but is useful for diagnosing failures. |
