# Claude Code hooks

Two Node hook scripts, wired in `.claude/settings.json` (shared, tracked).
`settings.local.json` holds only the machine-local permission mode.

Both scripts read the hook event as JSON on **stdin** (Claude Code sets no
`$TOOL_INPUT` env var — bash one-liners grepping it never fire), resolve the
repo root from `CLAUDE_PROJECT_DIR` with an `__dirname` fallback, and exit 0
on any error so they can never break a session.

## posttool-nudge.js — PostToolUse (`Edit|Write|Bash|PowerShell`)

Emits `hookSpecificOutput.additionalContext` (the only PostToolUse channel
the model actually sees) to nudge the agent to:

- update `guides/<guide>/markdown/<mirror>.md` after an Edit/Write to
  `guides/<guide>/chapters/*.tex` (vol-learning-guide `NN-slug.tex` →
  `chNN-slug.md`, number collisions resolved by slug against the real
  markdown listing; vol-project-ref is a 1:1 rename; `_*.tex` ignored)
- run the progress-log skill after a `git commit`

## guide-autosync.js — Stop

Per-guide sha256 signature over `chapters/*.tex` for **vol-learning-guide
and vol-project-ref**, compared against `.claude/.guide-sync-marker`
(gitignored JSON map `{guide: lastSyncedSignature}`; legacy bare-hex means
vol-learning-guide). When a guide's committed source (clean chapters dir)
differs from the marker, the hook blocks the Stop with instructions to
regenerate the mirrors and run sync-docs. Loop safety: the marker entry is
updated at fire time, and the sync output never touches chapter source.
Guides absent from the marker are seeded silently as already-synced, so
fresh clones don't trigger a pointless full regen+push.

## Tests

    node --test .claude/hooks/__tests__/*.test.mjs
