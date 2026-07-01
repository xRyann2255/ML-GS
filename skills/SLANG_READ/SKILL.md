---
name: SLANG_READ
description: "Read Slang script content — VFS-first (zero allows), secexpr/CVS fallback"
---

# SLANG_READ — Read Script Content

> **Purpose:** Read the current content of any Slang script. Uses VFS as primary path (zero terminal commands, zero allows). Falls back to secexpr `--safe` or CVS only when VFS is unavailable.

**Out of scope:** Editing, creating, deleting scripts (use `SLANG_EDIT`). Revision history/diffs (use `CVS`).

---

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `SLANG_READ` |
| **Scope** | Read current content of Slang scripts |
| **Inputs** | Script name, DB path (optional) |
| **Outputs** | Script source text |
| **Authority** | Read-only |

## When to Use

- Read the current content of a Slang script before editing or reviewing.
- Inspect a script's structure, functions, or linked dependencies.
- Verify script content after an edit operation.

---

## Decision Tree

```
Is the Slang extension VFS available? (list_dir("slang:/") succeeds)
  NO  → secexpr --read (Section B)
  YES ↓

Is the script in the userdb?
  YES → read_file("slang:/!{USERDB_PATH}/{script}.s")
  NO  → read_file("slang:/!NYC_Source/{script}.s")
        If not found → secexpr --read (Section B)
```

---

## Section A — VFS Path (Primary, Zero Allows)

### A1. Read from userdb

Discover the userdb path via `list_dir("slang:/")`.

```
read_file("slang:/!{USERDB}/{script_name}.s")
```

### A2. Read from ProdSource

```
read_file("slang:/!NYC_Source/{script_name}.s")
```

### A3. Read colon-named scripts

VFS **can read** colon-named scripts (the `:` restriction only applies to writes):

```
read_file("slang:/!NYC_Source/Test: My Script.s")
```

### A4. List scripts in a database

```
list_dir("slang:/!{USERDB}")
```

### Tips

- Both userdb and ProdSource paths work for reading
- If unsure where a script lives, try `!NYC_Source/` first (covers production)
- VFS renders tabs as spaces — content is functionally identical but whitespace may differ from raw storage

---

## Section B — secexpr Fallback

Use when VFS is unavailable (extension not installed) or script cannot be found via VFS.

### B1. Read via edit.py — Task-Based (Zero Allow, Preferred)

Use `run_task("slang-edit")` to run `edit_task.cmd` without terminal Allow prompts:

1. **Write args file** — `create_file` to `workspace/tmp/edit_args.json`:
   ```json
   {
     "db": "~{kerberos}!clean",
     "script": "{script_name}",
     "read": true,
     "run_id": "unique_id_here"
   }
   ```

2. **Launch task** — `run_task`:
   ```
   run_task("slang-edit", workspaceFolder: "h:\ml-vol-estimator")
   ```
   The task reads `workspace/tmp/edit_args.json` automatically.

3. **Poll with `read_file`** — read `workspace/tmp/slang_edit_results.json`.
   Wait until `"status": "done"` and `"run_id"` matches.

4. **Use results** — the `"content"` field contains the full script text.

See SLANG_EDIT Task-Based Execution for full details.

### B2. Read via edit.py — Terminal (1 Allow)

Only if task-based execution is unavailable:

```powershell
& PYTHON skills/SLANG_EDIT/src/edit.py --db "~{kerberos}!clean" --script "{script_name}" --read
```

The wrapper enforces `secexpr --safe` automatically. The `--db` path is your userdb (e.g. `~vicenf!clean`, `~vicenf!commit`).

ProdSource scripts are auto-resolved (no `--from-prod` needed for reads).

### B3. Read via CVS (specific revision)

Use CVS only when you need a **specific historical revision**, not current content:

```powershell
cvs co -r 1.49 -p slang/lib/misc/{PascalCaseName}.s 2> $null
```

---

## Section C — CVS (History Only)

CVS is for revision history, diffs, and blame — NOT for reading current content.

| Use Case | Tool |
|---|---|
| Current content | VFS (Section A) or secexpr (Section B) |
| Historical revision | `cvs co -r REV -p` |
| Diff between revisions | `cvs rdiff -u -r OLD -r NEW` |
| Blame/annotate | `cvs rannot -r REV` |
| Revision log | `cvs rlog -l` |

See `CVS` skill for full CVS commands.

---

## Performance Comparison

| Method | Time | Allows |
|---|---|---|
| VFS `read_file` | ~1s | 0 |
| secexpr `--read` (task) | ~28-40s | 0 |
| secexpr `--read` (terminal) | ~28-40s | 1 |
| CVS `co -p` | ~5-10s | 1 |

**Always prefer VFS.** It's 30x faster and requires zero user interaction.
When VFS is unavailable, prefer task-based secexpr (0 Allows) over terminal.

---

## Related Skills

| Skill | When |
|-------|------|
| `SLANG_EDIT` | Need to modify/create/delete a script |
| `CVS` | Need revision history, diffs, or blame |
| `SLANG_GLIMPSE` | Search for scripts by content |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Script not found | Wrong database or script name | Verify db path and exact script name including prefix |

## Links

- memory/slang/run.md — Slang execution and script access methods
