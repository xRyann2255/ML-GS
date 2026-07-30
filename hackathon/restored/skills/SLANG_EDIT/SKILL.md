---
name: SLANG_EDIT
description: Edit, create, and manage Slang scripts — VFS-first, secexpr fallback
---

# SLANG_EDIT — Modify and Create Scripts

> **Purpose:** Edit, create, rewrite, read, and delete Slang scripts. Two paths available — choose the right one per the decision tree below.
> **Scope:** CRUD on Slang scripts | **Authority:** Read + Write | **Out of scope:** running, testing, lint, code review

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `SLANG_EDIT` |
| **Scope** | CRUD operations on Slang scripts |
| **Inputs** | Script name, content, DB path |
| **Outputs** | Updated/created script confirmation |
| **Authority** | Read + Write (secexpr --safe) |

## When to Use

- Edit, create, delete, rewrite, or rename Slang scripts (including colon-named scripts).

---

## Decision Tree — Which Path to Use

```
Is the Slang extension VFS available? (list_dir("slang:/") succeeds)
  NO  → secexpr (Section B) for ALL operations
  YES ↓

Is the operation a READ?
  YES → VFS always works (even for colon-named scripts)

Is the script name contain ":"?
  YES → secexpr (Section B) for writes
  NO  → Is the operation DELETE?
          YES → secexpr (Section B)
          NO  → VFS (Section A)
```

**Extension check:** Call `list_dir("slang:/")` once per session. If it returns database folders, VFS is available. If it errors, fall back to secexpr for everything. VFS edits require **zero terminal commands** and zero "allow" prompts.

---

## Section A — VFS Path (Primary, Zero Allows)

The Slang extension registers a `slang:/` virtual filesystem. Scripts appear as regular `.s` files that can be read and edited with standard file tools.

### VFS Path Format: `slang:/!{DB_PATH}/{script_name}.s`

Discover DBs via `list_dir("slang:/")`. ProdSource: `slang:/!NYC_Source/`.\nDB paths: `slang:/!{USERDB}/` (read+write), `slang:/!NYC_Source/` (read+write, writes create overlay).

### A1. Read a script

```
read_file("slang:/!{DB_PATH}/{script_name}.s")
```

No terminal. No allow. Works for both userdb and ProdSource scripts.

For ProdSource scripts not in the userdb:
```
read_file("slang:/!NYC_Source/{script_name}.s")
```

### A2. Edit a script (partial replacement)

```
replace_string_in_file(
  path  = "slang:/!{DB_PATH}/{script_name}.s",
  old   = "OldCode()",
  new   = "NewCode()"
)
```

No terminal. No allow. Works for single and multi-line changes. For multiple independent edits, use `multi_replace_string_in_file`.

### A2b. Deleting multiple functions (sequential pattern)

→ See `memory/slang/best-practices.md` § "Deleting Multiple Functions" for the full pattern.

For secexpr-path scripts (colon names), use `--edit-file` with `delete-between` operations instead.

### A3. Full rewrite

Read current content, then replace ALL of it:

```
1. read_file → capture full text
2. replace_string_in_file(old = <entire content>, new = <new content>)
```

### A4. Create a new script

```
create_file("slang:/!{DB_PATH}/{new_script_name}.s", content)
```

**Note:** `create_file` via VFS can introduce minor whitespace artifacts. After creating, verify with `read_file` and fix if needed.

> VFS limits: `:` in script name → cannot write via VFS → use secexpr. DELETE not supported via VFS → use secexpr.

---

## Section B — secexpr Path (Fallback)

Use when VFS cannot handle the operation: colon-named scripts, deletes, or when the Slang extension is unavailable.

**MANDATORY: Always `secexpr --safe`.** Never use `--full`. The edit.py wrapper enforces this automatically.

**All text inputs must be pure ASCII.** Non-ASCII characters are rejected with an error.

> **Python:** Resolve `PYTHON` via the PYTHON_PATH skill before running commands.

Find secexpr: `cmd /c "H:\all-languages-env.cmd >nul 2>&1 && where secexpr"`

### B2. Single replacement (--old / --new)

```powershell
& PYTHON skills/SLANG_EDIT/src/edit.py ^
    --db "!NYC UserDBs!home!{kerberos}!clean" ^
    --script "Test: Foo" --old "OldCode()" --new "NewCode()"
```

For multi-line text, use `--old-file` / `--new-file` (point to tmp files).

### B3. Batch multi-edit (--edit-file)

Write a JSON array of operations, pass with `--edit-file`. All operations execute atomically.

```powershell
& PYTHON skills/SLANG_EDIT/src/edit.py ^
    --db "!NYC UserDBs!home!{kerberos}!clean" ^
    --script "_LIB Foo" --from-prod --edit-file workspace/tmp/edits.json
```

#### Supported operations

| Action | Fields | Description |
| --- | --- | --- |
| `replace` | `old`, `new` | Replace all occurrences |
| `delete` | `old` | Delete all occurrences |
| `delete-between` | `start_marker`, `end_marker` | Delete from start marker through end marker (inclusive) |
| `prepend` | `text` | Prepend to script |
| `append` | `text` | Append to script |
| `insert-before` | `marker`, `text` | Insert before first occurrence of marker |
| `insert-after` | `marker`, `text` | Insert after first occurrence of marker |

JSON escaping: `\n` newline, `\t` tab, `\"` double-quote, `\\` backslash — tool converts to Slang `Chr()` calls automatically.

### B4. Other operations

```powershell
--prepend-file workspace/tmp/header.txt    # prepend from file
--append "SmartLinkEnable();"              # append text
--read                                     # print current text
--trim-leading-blank-lines                 # remove leading blanks
--check-ascii                              # check for non-ASCII
--create --content-file workspace/tmp/c.s  # create new script
--rewrite --content-file workspace/tmp/c.s # replace entire content
--delete                                   # delete script
```

### B5. ProdSource resolution (--from-prod)

Read-only operations auto-include ProdSource. `--from-prod` needed only for the **first write** to a ProdSource-only script (creates a user-db overlay).

| Script location | Read | Write |
| --- | --- | --- |
| Already in userdb | Normal | Normal |
| In ProdSource only | Normal | `--from-prod` required |
| Brand new | N/A | Use `--create` |

---

## Limitations

- **No undo**: `UpdateSecurity` commits immediately — use CVS for rollback
- **Whitespace**: DB stores tabs; VFS renders as spaces
- **VFS colon restriction**: `:` in names → falls back to secexpr automatically
- **Backslashes**: Slang treats `\` as escape; double them in JSON (`\\`)

---

## Task-Based Execution (Zero Allow — secexpr Fallback)

When using the secexpr path (colon-named scripts, deletes, or VFS unavailable),
run `edit.py` via a VS Code Task to avoid terminal "Allow" prompts entirely.
The agent never uses `run_in_terminal` — all interaction is through `run_task`
(to launch) and `read_file` (to poll results).

### Workflow

1. **Write args file** — `create_file` to `workspace/tmp/edit_args.json`:
   ```json
   {
     "db": "~jdoe!commit",
     "script": "Test: My Script",
     "read": true,
     "run_id": "unique_id_here"
   }
   ```

2. **Launch task** — `run_task("slang-edit")`:
   ```
   run_task("slang-edit", workspaceFolder: "h:\ml-vol-estimator")
   ```
   The task reads `workspace/tmp/edit_args.json` automatically.

3. **Poll with `read_file`** — read `workspace/tmp/slang_edit_results.json`.
   Wait until `"status": "done"` and `"run_id"` matches. No terminal needed.

4. **Use results** — parse `exit_code`, `output`, and `content` (for reads) from the JSON.

Args keys mirror CLI flags (snake_case): `db`, `script`, `old`, `new`, `old_file`, `new_file`, `edit_file`, `prepend`, `prepend_file`, `append`, `append_file`, `content_file`, `read`, `delete`, `create`, `rewrite`, `check_ascii`, `trim_leading_blank_lines`, `from_prod`, `dry_run`, `output_json`, `run_id`.

Result JSON: `{"status": "done", "run_id": "...", "script": "...", "exit_code": N, "output": "...", "content": "..."}`. Exit codes: 0 = success, 1 = error, 2 = no change (old text not found). `content` field present only for `--read`.

### CRITICAL: No `run_in_terminal` anywhere

| Step          | Tool                  | Why                          |
| ------------- | --------------------- | ---------------------------- |
| Write args    | `create_file`         | JSON input — no terminal     |
| Launch edit   | `run_task`            | VS Code Task — no Allow      |
| Poll results  | `read_file`           | File read — no terminal      |
| Parse results | *(in-agent)*          | JSON parse — no terminal     |

### Notes

- **`edit_task.cmd`** auto-detects Python from `H:\venv*` (highest version first)
- Default output: `workspace/tmp/slang_edit_results.json`
- File starts with `{"status": "running", "run_id": "..."}`, then overwrites with `{"status": "done", ...}` on completion
- Always generate a unique `run_id` and match it when polling to avoid stale results

---

## Troubleshooting

→ See `memory/_dormant/slang/secexpr-gotchas.md` for comprehensive troubleshooting (UpdateSecurity returns 0, text not found, secexpr not found, NTFS colon errors, etc.).

## Links

- memory/slang/lint-edit.md — edit patterns, overlay types
- memory/_dormant/slang/secexpr-gotchas.md — secexpr pitfalls
- memory/_dormant/slang/headers.md — canonical Slang header patterns
- memory/_dormant/slang/run.md — running scripts in VS Code
