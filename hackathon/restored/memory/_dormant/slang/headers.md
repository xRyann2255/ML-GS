---
created: 2026-04-08
updated: 2026-04-15
tags: [slang, headers, templates, scripts]
status: dormant
relates:
  - slang/formatting.md
  - slang/best-practices.md
---

# Slang Script Headers

## Date Format

`Created` uses `DDMonYY` with leading space for single digits: ` 8Apr26`, `15May26`.

**New scripts MUST use the current date.** Never leave Created blank or copy a date from another script. Example for April 30, 2026: `30Apr26`.

## Common Header Template

All scripts share this structure (only `Script Type` and `Features` differ):

```slang
/****************************************************************
**
** Script Name : {prefix} Name
** Script Type : {type}
** Summary     : {brief summary}
** Test Script : {test script name}
** Notifyees   : EL{eq-strategy-intl-nyc}
** Features    : {features if applicable}
** Created     :  9Apr26
** Description :
**     {description}
**
** Copyright 2026 - Goldman Sachs
**
** $Log:$
****************************************************************/
```

## Mandatory Rules

- **ALL scripts MUST have a filled-in header.** Never leave `Summary` or `Description` blank — if editing a script with an empty header, fill it in even if you didn't create the script.
- **`$Log:$` is a CVS keyword — NEVER use `** Log :` as a field name.** The ScriptReview header parser (`@Script::Entitlements From Header`) rejects `Log :` as an invalid header entry. Always use `** $Log:$` as the LAST entry before the closing `*********/` line. CVS expands this into revision history automatically after the first commit.
- **Field ordering matters.** The canonical order is: Script Name, Script Type, Summary, Features, Test Script, Notifyees, Created, Description, Copyright, `$Log:$`.
- **Test Script field: APPEND, never replace.** When a script already has RegTests linked (e.g. `Test: Script Lints Without Err`), APPEND the new RegTest with a comma — never overwrite the existing value. Example: `** Test Script : Test: Script Lints Without Err` → `** Test Script : Test: Eq Brazil Acct Import,Test: Script Lints Without Err`. Only replace if the existing value is empty.
- **Script name casing is SACRED.** Never change the casing of a script name when referencing it in code, reviews, or edit.py commands. Script names are case-sensitive in CVS, ScriptReview, and display contexts. Always use the EXACT original casing (e.g. `_SSP Eq Brazil ETI`, not `_Ssp Eq Brazil Eti`). If unsure, read the script header's `Script Name` field.
- **Header is IMMUTABLE on revert.** When reverting local changes, never touch the top header comment block — it contains CVS `$Log:$` metadata managed by the system. Only revert the code body.

## Per-Type Differences

| Type | Prefix | Description | Notes |
|------|--------|-------------|-------|
| Config | `_CFG` | Configuration scripts | |
| Library | `_LIB` | Reusable function libraries | End with `SmartLinkEnable();`. Features: `AllFunctionsDocumented, Tested` |
| Process | `_PROCM` | Procmon jobs | Features: `AllFunctionsDocumented` |
| Utility | `_UT` | User utilities (usually has UI) | |
| App | `_APP` | User utilities (usually has UI) | |
| Apache | `_Apache` | Apache configuration | |
| SUIT | `_SUIT` | SUIT definition (UI related) | |
| Typed Structure | `_TYPE` | Typed structure definition | |
| Plex Pool | `_PLEX` | Plex pool configuration | |
| CDL | `_CDL` | CDL configuration | |
| Constants | `_CONST` | Constant definitions | |
| SSP | `_SSP` | Slang Server Pages | |
| JSX | `_JSX` | React pages served by special SSP | |
| Quote Tool | `_QT` | Quote Tool definition | |
| Documentation | `_SLAM` | Slang documentation | |
| Trade Validation | `_Trade` | Trade validation functions | |
| RegTest | `Test:` | Regression test scripts | Links: `_LIB FasTest`, `_LIB RegTest Fns`, `_Slang RegTest Stub Function`. End with `@FasTest::Go(...)` |
| Example | `Example:` | Example scripts | |
| UFO | `UFO` | Graph/security definition | |

## Common Rules

- `Notifyees` always `EL{eq-strategy-intl-nyc}`
- `Copyright` year = current year
- `$Log:$` always last before closing `*********/`
- Fill in `Summary` and `Description`
- **MANDATORY:** ALL scripts must have a top header with a description. If editing a script with an empty/missing header, you MUST fill it in — even if you didn't create the script. Never leave `Summary` or `Description` blank.
