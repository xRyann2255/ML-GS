---
created: 2026-04-29
updated: 2026-04-29
tags: [sys, jsi, idea-jsi, intellij, ide, secdb, sdlc, java, review, jsiview, migration]
status: dormant
relates:
  - sys/secdb-ecosystem.md
  - sys/secdb.md
---

# idea-jsi — IntelliJ-based JSI IDE

IntelliJ plugin + secexpr sidecar for JSI (Java Slang Integration) development. Replaces legacy `jsiview` (IntelliJ 2016). Runs on vanilla IntelliJ 2024. Git-backed local workflow that syncs to SecDB on compile/submit.

**Page hierarchy:** Enterprise Platforms > SecDb Platform > JSI SDLC > JSI SDLC IDE > IDEA JSI
**Migration deadline:** jsiview EOL end of 2026 Q2 (JetBrains license server incompatibility with IntelliJ 2016).

---

## Architecture

```
SecDB SOURCE
  ↓ (periodic sync job by JSI SDLC team)
Remote GitLab: gitlab.aws.site.gs.com/jsi/jsi/modules
  ↓ (sparse + shallow local clone)
Local git repo (HEAD = master, read-only)
  ↓ (developer creates feature branch)
Local feature branch: feature-<kerberos>-<name>
  ↓ (on Compile / Test / Review)
Ephemeral SecDB branch: <kerb>!JG_<git-branch-suffix>_<start-of-week>;SOURCE
  ↓ (compilation / execution)
SecDB runtime
```

- **Sparse-checkout:** Only modules you import are checked out (not the full JSI mono-repo).
- **Shallow repo:** Truncated commit history — keeps clone fast but limits `git blame` and can break rebasing.
- **Sidecar:** A JSIVM process that handles JSI-specific API communication (compile, sync, review, etc.).

## Requirements & Setup

- **Disk:** ≥6GB free on H:\
- **RAM:** Ideally 12GB free (freezes if insufficient)
- **Launch:** Run `idea-jsi` in a terminal (auto-downloads binaries on first run)
- **Git path:** `I:\sw\ficc\wraps\bin\git.cmd` (Windows), `/sw/ficc/wraps/bin/git` (Linux)

## Command-Line Options

| Flag | Default | Description |
|------|---------|-------------|
| `-v` / `--verbose` | — | Increase logging verbosity |
| `-i` / `--install-only` | — | Install only, don't launch |
| `--Xmx=<arg>` | `8G` | Max JVM heap for IntelliJ process |
| `--sidecar-memory=<arg>` | `4G` | Max memory for sidecar JSIVM |
| `--sidecar-port=<arg>` | `0` | Sidecar port (when launched separately) |
| `--sidecar-branch-override=<arg>` | — | Override sidecar MS (default: `JSICore`) |
| `--beta` | — | Use latest unreleased version from master |
| `--skip-sidecar` | — | Don't auto-launch sidecar (pair with `--sidecar-port`) |

## Quick Start

1. Run `idea-jsi` → wait for binaries download
2. Select **New JSI Project** → point to an **empty** folder
3. Default branch (`master`) is **read-only** → create a new branch immediately
4. Create branch: **JSI > Branches > New Branch** (NEVER use git commands or IDEA's git interface)
5. Import modules: **JSI > Modules > Import JSI Modules**
6. Ready to work

## Key Workflows

| Action | How |
|--------|-----|
| Compile | Ctrl+S → Ctrl+F9 (syncs to JSI + compiles). Ctrl+Shift+F9 = changed modules only |
| Rebase | Ctrl+T (prefer rebase over merge) |
| Force sync | JSI > Sync > Sync JSI Project, or Ctrl+F9+F9 |
| Submit review | JSI > Review > Submit Review (Ctrl+Shift+K) |
| Full library recon | JSI > Recon > Full Library Recon (fixes dependency wiring) |
| Git blame | JSI > VCS > Get Annotations for Current File (shallow clone — truncated history) |
| Add Slang branch | Run Configuration → enter Slang Branch → executes on union DB |
| CLM scan | JSI > Dependencies > Run CLM Scan (vulnerability check) |
| Glimpse search | JSI > Glimpse (searches JSI, Slang, Procmon codebases) |

## JSI Menu Actions Reference

### Branches
- **New Branch:** Creates local git branch + wires SecDB ephemeral branch. Naming: `feature-<kerb>-<name>` (name ≥4 chars).
- **Snap from Branch:** ⚠️ **Destructive** — replaces ALL local changes with selected branch. No undo.

### Modules
- **Import Modules:** Pick from list of all JSI modules. Click **Refresh Module List** if missing.
- **Import Module for Current File:** One-click import for the file's module.
- **Import All Edited Modules:** After Snap from Branch — imports all changed modules + changeset.
- **Create Module:** Create new JSI module via form dialog.
- **Go To Repository:** Opens current module/file in GitLab browser.
- **Show Sensitivity:** Displays Sensitivity Procedure for current module/file.

### Build
- **Compile Project (Ctrl+F9):** Syncs tracked changes to ephemeral SecDB branch + compiles. Only **git-tracked** files included (untracked silently excluded).
- **Compile Changed Modules (Ctrl+Shift+F9):** Faster — only compiles changed modules, no dependents.

### Review
- **Submit Review (Ctrl+Shift+K):** Files must be committed first (Ctrl+K / git commit). All commits squashed into single JSI commit. Staged-only changes synced.
- **Import Review:** Enter review ID → select files to import into current project (copies files only).

### Sync
- **Sync JSI Project:** Manual sync to ephemeral branch (same as pre-compile sync).
- **Fetch Covering Commits:** Fetches enough remote history to cover local tags/heads. Fixes "disjointed" shallow history that causes rebase failures.

### Recon
- **Full Library Recon:** Fixes red/unresolved library references (reconciles both library deps + CAS refs).
- **Recon Library Dependencies / Recon CAS:** Targeted reconciliation.

### Dependencies (Maven Artifact Repository)
- **Add (+):** Fill form → Find → select version → OK. Then **Deploy** to distribute to `I:\sw`.
- **Remove (−):** ⚠️ Removes from **ALL of JSI**, not just your project.
- **Deploy:** Distributes to `I:\sw`. Deployed deps expire after **1 month** if not promoted to PS.
- **List Primary / Transitive Dependencies:** Show direct or full dependency chain.

### Shared Dev (SDB Rebase)
- **Start SDB Rebase:** Creates scratch branch, then rebase via Ctrl+T or CLI.
- **Propagate SDB Changes:** After rebase, pushes to SecDB. Opens release page on success.
- **End SDB Rebase:** Deletes scratch branches, concludes rebase.

## Staged vs Unstaged — What Gets Synced

| Operation | What syncs to SecDB branch |
|-----------|---------------------------|
| Compile / Test (Ctrl+F9) | Both staged AND unstaged diffs |
| Review submission (Ctrl+Shift+K) | **Staged only** (committed changes) |

## Critical Rules

- **NEVER create branches with git commands** — always use JSI menu (plumbing + validation)
- **NEVER push with git commands** — no mechanism to propagate from GitLab → SecDb
- **All top-level objects must be directories** (JSI modules) — root-level files break sync
- **New files:** Always say YES when IDEA asks to add to git — only git-tracked files sync to JSI
- **Generated files** (annotation processors) don't need to be staged — build server generates them
- **SecDB Object DB:** Set as VM property in run/test config (jsiview's `--jsidb` flag doesn't exist)

## Ephemeral Branches

- Naming: `<kerb>!JG_<git-branch-suffix>_<start-of-week>;SOURCE`
- Purged and recreated periodically — **never run production workloads** off these
- Created on compile/test/review actions

## Differences from jsiview

| Aspect | jsiview | idea-jsi |
|--------|---------|----------|
| IntelliJ version | Modified 2016 | Vanilla 2024 (plugin) |
| Backing store | SecDB (immediate) | Git → local FS (sync on demand) |
| Source of truth | SecDB | GitLab (mirrored from SecDB) |
| Mixed review (Slang+JSI) | Supported | Not supported (submit separately) |
| Multiple branches | Concurrent | One per project (use multiple projects) |
| Object DB flag | `--jsidb=<db>` on CLI | VM property in run/test config |
| Blame/annotations | Direct SecDB history | Shallow git (may be truncated) |

## Gotchas & Tips

1. **Untracked files silently excluded** from compile sync. Must `git add` new files — no error if missed.
2. **Ephemeral branch not stable** — never point PROCM jobs or Freddie zones at `JG_*` branches.
3. **Snap from Branch is destructive** — replaces entire local branch content. No partial import.
4. **Maven dep removal is global** — affects all of JSI, not just your project.
5. **Deployed Maven deps expire after 1 month** if not promoted. Re-deploy if dev continues.
6. **Shallow repo breaks rebasing** — run **Fetch Covering Commits** if fast-forward rebase fails.
7. **Git blame truncated** — use JSI > VCS > Get Annotations (has mitigations); raw `git blame` unreliable.
8. **Force compile sync** — press Ctrl+F9 twice quickly (Ctrl+F9+F9) if sync was skipped.
9. **Old review lookback is 30 days** — to update older reviews: run custom sidecar with patched `_LIB Script Review Load Fns` (change `Start Date` from `Today() - 30`), launch via `jsivm --source "<branch>" --jsiproject=jsi-intellij-vfs-server com.gs.jsi.intellij.vfs.server.api.VfsServer <port>`, then run IntelliJ with `--skip-sidecar --sidecar-port=<port>`.
10. **Object DB is a VM property** now, not `--jsidb` CLI flag.

## Support

- **Symphony:** JSI Main Room (best for questions), JSI IDE Bug Reports, JSI IDE Beta Testers
- **Email:** gs-sdlc-jsi@internal.email.gs.com
- **FAQ:** Common JSI User Questions on EPSSP
- **GitLab:** `gitlab.aws.site.gs.com/jsi/jsi/modules`
- **Plugin repo:** `gitlab.aws.site.gs.com/developer-experience/jsi-sdlc/intellijsi-core`

## Confluence Sources

| Page ID | Title |
|---------|-------|
| 5802457468 | IDEA JSI (parent) |
| 4676621033 | Getting Started with idea-jsi |
| 7662446036 | idea-jsi JSI Menu Actions |
| 7662446203 | Understanding idea-jsi |
| 7662446342 | Command Line Options in idea-jsi |
| 5802457470 | idea-jsi Tips & Tricks |
| 7323545851 | JSIView Demise — Migration High Level Points |
| 7319398002 | idea-jsi Features Development |
| 7338280168 | idea-jsi Features Inventory |
| 7406190060 | idea-jsi shared dev support |
| 7488887874 | JSI IDE Usage |
| 7338270303 | JSIView Demise Monitoring |
| 7722292582 | idea-jsi with Managed Slang and Shared Dev |
