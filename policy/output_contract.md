# Output Contract

## Response Format by Task Type

| Task Type | Format |
|-----------|--------|
| Implementation | Brief confirmation + list of changed files with line-range links |
| Debugging | Root cause (1-2 sentences) + fix applied + verification evidence |
| Code review | Annotated findings table: file, line, severity, comment |
| Research / explanation | Prose with source citations; no fabricated references |
| Refactor | Changed files, behaviours preserved, behaviours removed, known risks |
| Planning | Numbered task list with acceptance criteria per item |

## Quality Standards

- **Evidence-first:** Claims about code behaviour must be backed by terminal output or file reads, not inference.
- **Completeness:** Do not stop at partial output. If a task has 3 steps, deliver all 3.
- **Brevity:** Match depth to complexity — simple answers in 1-3 sentences; complex work in structured sections.
- **No fabrication:** If a file, symbol, or API cannot be found after a search, say so. Do not invent plausible-sounding alternatives.
- **Linked references:** File mentions must use markdown links with line numbers where applicable.
