---
name: SLANG_TEST_COVERAGE
description: Fetch test coverage data from EPSSP Sensitive Slang Procedure page and report untested scripts
---

# SLANG_TEST_COVERAGE — Test Coverage Report

> **Purpose:** Fetch script data from the EPSSP Sensitive Slang Procedure page and generate a prioritized report of scripts missing tests, ordered by reference count and size.

**Out of scope:** Writing tests, editing scripts, running lint.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `SLANG_TEST_COVERAGE` |
| **Scope** | Fetch EPSSP procedure scripts and report test coverage gaps |
| **Inputs** | Procedure name + ID (defaults to Eq1D Brazil / 503) |
| **Outputs** | Coverage report to `workspace/tmp/epssp_coverage_out.txt` |
| **Authority** | Read-only (HTTP GET via Kerberos, no secexpr) |

## When to Use

- To identify which scripts in a procedure need RegTests.
- To prioritize test writing by impact (most-referenced, largest scripts first).
- To get a snapshot of test coverage metrics (function, decision, condition coverage).

## Quick Start

1. Write args file to the fixed path `workspace/tmp/slang_test_coverage_args.json` (this is the literal `--args-file` value in the `slang-test-coverage` task definition — see `ml-vol-estimator.code-workspace`). The args file path is fixed per task — two concurrent agents writing it race (last writer wins). Keep `out_file` unique per run (put a `run_id` slug in its name); the args file itself is not collision-safe.

```json
// workspace/tmp/slang_test_coverage_args.json
{
  "procedure": "Eq1D Brazil",
  "id": "503",
  "out_file": "workspace/tmp/epssp_coverage_out.txt"
}
```

2. Run via task: `run_task(id="slang-test-coverage")`

3. Read results: `read_file("workspace/tmp/epssp_coverage_out.txt")`

## Arguments

| Key | Req | Default | Description |
|-----|-----|---------|-------------|
| `procedure` | No | `Eq1D Brazil` | SSP procedure name |
| `id` | No | `503` | SSP procedure ID |
| `out_file` | No | `workspace/tmp/epssp_coverage_out.txt` | Output report path |
| `prefixes` | No | `["_LIB", "_PROCM", "_UT"]` | Script prefixes to include |
| `cache_file` | No | _(none)_ | Path to cached JSON; skips HTTP fetch if file exists |
| `show_all` | No | `false` | Show all scripts (not just untested) |

## Output

The report contains:

1. **Summary** — Total script counts by type and testing status
2. **Per-prefix tables** — Scripts not fully tested, sorted by Refs (Total) DESC then Lines DESC, showing:
   - Script name, line count, direct/total references
   - Testing status (Not Tested / Not Possible / N/A)
   - Total coverage %, test script name

## Data Source

EPSSP AJAX endpoint:
- **URL:** `https://www.epssp.site.gs.com/ssps/Current/Sensitive_Slang_Procedure`
- **Method:** POST with `{"action": "slang-scripts-tab-data", "procedure": "...", "id": "..."}`
- **Auth:** Windows Kerberos via PowerShell `UseDefaultCredentials`

## Caching

To avoid repeated HTTP fetches, pass `cache_file`:

```json
{
  "cache_file": "workspace/tmp/epssp_scripts.json",
  "procedure": "Eq1D Brazil",
  "id": "503"
}
```

If the cache file exists, data is loaded from it. Delete the file to force a fresh fetch.

## Links

- EPSSP page: `https://www.epssp.site.gs.com/ssps/Current/Sensitive_Slang_Procedure?Id=503&Procedure=Eq1D+Brazil`
- memory/_dormant/slang/regtest.md — RegTest conventions
