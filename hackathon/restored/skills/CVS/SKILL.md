---
name: CVS
description: "Inspect CVS revision history, produce diffs, and compare versions of Slang and other files."
---

# CVS — Concurrent Versions System

> **Purpose:** Inspect revision history, produce diffs, and compare versions of Slang (`.s`) and other files stored in the GS CVS repository. **Read-only — never commits, tags, or modifies the repository.**

**Out of scope:** CVS commits, tagging, branching, merges, checkouts (working-copy management).

---

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `CVS` |
| **Scope** | `rlog`, `rdiff`, `rannot` — server-side read operations only |
| **Inputs** | Repository-relative file paths |
| **Outputs** | Revision lists, unified diffs, commit metadata, Markdown diff reports |
| **Authority** | Read CVS server only; does NOT write to workspace files unless user requests a saved report |

---

## When to Use

- User asks about revision history, version diffs, blame/annotate, or "who changed this".
- Need to compare HEAD vs previous revision of a Slang script.

---

## Memory Loading Policy

| Task | Load |
|------|------|
| Simple `rlog` / `rdiff` | **Nothing** — SKILL.md has all commands inline |
| Need CVS module path conventions, path mapping | (not yet documented) |
| Environment setup, Kerberos / `kinit` | `memory/ref/devtools.md` |

---

## Prerequisites

| Variable | Value |
|----------|-------|
| `CVSROOT` | `:gserver;realm=GS.COM:cvshost.ficc.gs.com:/home/cvs` (pre-configured) |
| Client | CVSNT 2.5.05 (available on `$PATH` as `cvs`) |
| Auth | Kerberos (must have a valid ticket — run `kinit` if commands time out) |

No checkout directory is needed. All commands operate directly against the server via module paths.

---

## Task Execution (Preferred)

```json
// workspace/tmp/cvs_args.json
{
  "command": "rlog",
  "path": "slang/lib/misc/SpgRebalanceFns.s",
  "limit": 5,
  "out_file": "workspace/tmp/cvs_out.txt"
}
```

Commands: `rlog`, `rdiff`, `rannot`, `rls`, `co`

For `rdiff` with auto HEAD-vs-prev: `{"command": "rdiff", "path": "...", "head_vs_prev": true}`
For `rdiff` with explicit revisions: `{"command": "rdiff", "path": "...", "revisions": ["1.456", "1.457"]}`
For `rannot` with revision: `{"command": "rannot", "path": "...", "revisions": ["1.457"]}`
For `rls` with filter: `{"command": "rls", "path": "slang/lib/misc/", "pattern": "rebalance"}`
For `co` with revision: `{"command": "co", "path": "...", "revisions": ["1.456"]}`

Task label: `cvs`

---

## Core Commands (CLI reference)

### 1. Get revision log (most recent N revisions)

```powershell
# All revisions (can be very long):
cvs rlog slang/lib/misc/SpgRebalanceFns.s 2>&1

# Extract just revision + date lines, show top N:
cvs rlog -l slang/lib/misc/SpgRebalanceFns.s 2>&1 | Select-String "^revision|^date:" | Select-Object -First 10
```

> `-l` = local (no sub-dirs). Omit `-l` for directory-level summaries.

### 2. Diff two revisions — unified format

```powershell
cvs rdiff -u -r 1.456 -r 1.457 slang/lib/misc/SpgRebalanceFns.s 2>&1
```

> `rdiff` works without a checkout; output is standard unified diff.

### 3. Diff HEAD against previous revision

```powershell
# Step 1: get head and previous rev numbers
$revs = cvs rlog -l slang/lib/misc/SpgRebalanceFns.s 2>&1 |
        Select-String "^revision" |
        Select-Object -First 2

# Step 2: parse out the two revision strings
$head = ($revs[0] -replace 'revision ','').Trim()
$prev = ($revs[1] -replace 'revision ','').Trim()

# Step 3: diff
cvs rdiff -u -r $prev -r $head slang/lib/misc/SpgRebalanceFns.s 2>&1
```

### 4. Annotate — blame per line

```powershell
cvs rannot -r 1.457 slang/lib/misc/SpgRebalanceFns.s 2>&1
```

### 5. Get a specific revision to a temp file

```powershell
cvs co -r 1.456 -p slang/lib/misc/SpgRebalanceFns.s 2> $null > workspace/tmp/SpgRebalanceFns_1.456.s
```

> `-p` = print to stdout (no working copy created). Redirect stderr to `$null` to suppress CVS noise.

---

## Path Conventions

Slang library files live under the CVS module `slang/`:

| Slang script location | CVS path |
|-----------------------|----------|
| `_LIB` scripts in lib/misc | `slang/lib/misc/<PascalCaseName>.s` |
| User DB scripts | NOT in CVS — use the `slang:/` virtual FS instead |

**Mapping rule:** strip spaces, convert to PascalCase.
`_LIB SPG Rebalance Fns` → `SpgRebalanceFns.s`
`_LIB MLR Var Chooser Fn Params` → likely `MlrVarChooserFnParams.s`

When unsure of the exact path, use `cvs rls` to browse:

```powershell
cvs rls slang/lib/misc/ 2>&1 | Select-String -i "rebalance"
```

---

## Diff Report Template

After running a diff, produce a Markdown report in this format:

```markdown
## CVS Diff: slang/lib/misc/SpgRebalanceFns.s  1.456 → 1.457

| Field | Value |
|-------|-------|
| HEAD | 1.457 |
| Prev | 1.456 |
| Author | <kerb> |
| Date | 2026-04-02 |
| Lines | +11 / -0 |
| Review | 6010-2193957S |

### Summary
One-sentence description of what changed.

### Changed Areas
- Function `Foo`: added parameter `DB Override`
- Guard: conditional override of `Trade Program Container Db`

### Diff
\`\`\`diff
[unified diff output here]
\`\`\`
```

---

## Workflow: Diff HEAD vs Previous

1. Run `cvs rlog -l <file> | Select-String "^revision|^date:" | Select-Object -First 6` to get recent revisions.
2. Extract HEAD (`1.N`) and previous (`1.N-1`) from that output.
3. Run `cvs rdiff -u -r 1.(N-1) -r 1.N <file>`.
4. Render using the Diff Report Template above.

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `no such directory` | Path is wrong or you're using `cvs log` (needs checkout) | Switch to `cvs rlog` / `cvs rdiff` |
| `authorization failed` | Kerberos ticket expired | Run `kinit` in terminal |
| `cannot open CVS/Repository` | Running `cvs log` outside a working copy | Use `rlog`/`rdiff` instead |
| Output truncated | Very long log | Pipe to `Select-Object -First N` or use date range: `-d "2026-01-01<2026-04-08"` |

---

## Session State

Track in working memory when this skill is active:

| Field | Description |
|-------|-------------|
| `cvs_last_file` | Last file examined (`module/path/file.s`) |
| `cvs_head_rev` | HEAD revision number |
| `cvs_prev_rev` | Previous revision number |
| `cvs_diff_saved` | Path to saved diff in `workspace/tmp/` (if any) |

---

## Links

- CVS command reference, module paths, conventions (not yet documented in memory)
