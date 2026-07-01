---
created: 2026-03-16
updated: 2026-04-30
tags: [skills, shell, curl, logging, best-practices]
status: active
relates: []
---

# Skill Script Conventions

For shell scripts in `skills/*/src/`.

## Language Policy

| ID | Rule | Rationale |
|----|------|-----------|
| L1 | **Python is the required implementation language** for all new skill scripts | Cross-platform, testable, consistent with existing skill majority |
| L2 | **PowerShell is an anti-pattern** for skill implementation | Windows-only, not portable, harder to test/maintain |
| L3 | Use PowerShell ONLY when it is the sole possible solution (e.g., Windows COM/OLE interop with no Python equivalent) | Escape hatch for truly OS-specific needs |
| L4 | `.cmd` task wrappers remain valid (they only bootstrap Python) | Thin shims that call `python.exe script.py` are not "implementation" |
| L5 | Every read-only skill MUST have a VS Code task wrapper as the preferred execution method | Enables `create_file → run_task → read_file` flow; avoids `run_in_terminal` Allow prompts |

**Existing .ps1 files** (legacy — migrate to Python when next modified):
- `GIT/src/mr_task.ps1`
- `GITLAB_SEARCH/src/gitlab-search.ps1`
- `GITLAB_PIPELINES/src/fetch-pipeline.ps1`, `gitlab-auth.ps1`, `lint-ci-yaml.ps1`
- `KILL_ORPHANS/src/cleanup.ps1`
- `PYTHON_PATH/src/resolve.ps1`
- `SYNC_SUPPORT_MEMORY/src/accept.ps1`, `sync.ps1`

## HTTP Logging

Log **verb, URL, body** — nothing more. No `curl -v` (too noisy). Use `tee` for terminal+file.

```bash
echo "GET ${URL}" | tee "${LOG_FILE}"
HTTP_CODE=$(curl -s -o "${OUT_FILE}" -w "%{http_code}" -b "GSSSO=${GSSSO}" "${URL}")
echo "HTTP ${HTTP_CODE}" | tee -a "${LOG_FILE}"
```

Helper scripts outputting to stdout: log to stderr (`>&2`). Log file: `.log` next to output.

## File Output

- Save to `workspace/tmp/` with descriptive name. Always re-fetch (data changes).
- Validate JSON: `python3 -m json.tool "${OUT_FILE}"`.

## Task Wrapper Path Resolution

When running `.cmd` files via `run_task`, VS Code runs the command from the workspace root.
This means `%~dp0` resolves to the **workspace root**, not the original `.cmd` location.

**Workarounds:**
- Use **CWD-relative paths** (VS Code tasks run from workspace root): `set "MY_PY=skills\FOO\src\foo.py"`
- Use **environment variables** (`$env:VAR` in inline PowerShell) set before the PowerShell block.
- Never use `%~dp0` to locate sibling scripts in `.cmd` files run via `run_task`.
