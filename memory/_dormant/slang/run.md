---
created: 2026-03-26
updated: 2026-04-14
tags: [slang, vscode, extension, commands, shortcuts]
status: active
relates:
  - ref/devtools.md
  - slang/lint-edit.md
  - slang/best-practices.md
---

# Slang Extension — Run Scripts

Extension: `goldman-sachs.secview-extension`

## Key Shortcuts

| Action | Shortcut | Command ID |
|---|---|---|
| Run script | F9 | `slangScriptExplorer.runSlangScript` |
| Run selection | Shift+F9 | `slangScriptExplorer.runSlangScriptSelection` |
| CPU profiler | F8 | `slangScriptExplorer.runCPUProfiler` |
| Lint | Alt+L | `slangLanguageClient.lintScript` |
| Run FasTest | — | `slangScriptExplorer.fasTestRunWithDefaults` |
| FasTest (options) | — | `slangScriptExplorer.fasTestRun` |
| Zebra Farm | — | `slangScriptExplorer.zebraTestRun` |

## FasTest Workflow

- **In-session**: Ctrl+Shift+P → "Slang: Run FasTest"
- **Background**: choose "Run in background" from options
- **From library**: if header has `Test Script : Test: Foo`, FasTest runs associated tests

## Other Commands

| Action | Command ID |
|---|---|
| New script | `slangScriptExplorer.newSlangScript` |
| Rename | `slangScriptExplorer.renameCurrentSlangScript` |
| Delete | `slangScriptExplorer.deleteSlangScript` |
| Scratch pad | `slangScriptExplorer.scratchPad` |
| Toggle SAFE/FULL | `slangScriptExplorer.toggleSafeMode` |
| Refresh | `slangScriptExplorer.refresh` |

## Debugging

Shift+F1 (breakpoint), F5 (continue), F10 (step over), F11 (step into), Shift+F11 (step out). Debugger auto-launches on eval.

## VFS Editing (Primary Path)

The extension exposes a `slang:/` virtual filesystem. Agents can read/edit scripts directly:
- **Read**: `read_file("slang:/!{DB_PATH}/{script}.s")`
- **Edit**: `replace_string_in_file` on the VFS path (zero terminal, zero allows)
- **Create**: `create_file` on VFS path (verify content after — may have minor artifacts)
- **Multi-edit**: `multi_replace_string_in_file` for multiple changes in one script
- **Full rewrite**: read entire content, then replace all of it

Available databases visible via `list_dir("slang:/")`.

## Limitations

- `:` in filenames → VFS fails (NTFS alternate data stream error) → use SLANG_EDIT secexpr path
- DELETE → not supported via VFS → use SLANG_EDIT secexpr path
- `secexpr` not on PATH → use extension commands
- Output in Slang extension panel, not terminal
- DB stores tabs; VFS renders as spaces
