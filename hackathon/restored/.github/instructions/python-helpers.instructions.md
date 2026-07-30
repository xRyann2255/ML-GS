---
applyTo: "{skills,workspace}/**/*.py"
---

# Helper-Script Python Rules (skills/, workspace/)

Scope: skill scripts, lint modules, workspace scripts/presentation. The ML/data-access
instruction file (`python.instructions.md`) applies only to `src/**/*.py`.

## Environment
- Never invoke a bare interpreter. S-B (GS Linux Coder): `./vol shell <script>` or
  `./vol exec python ...`. S-A (GS Windows): the skill's `run_task` label, or `vol.cmd exec ...`
  for the dev loop.
- Interpreter resolution is owned by `skills/_shared/_run.sh` / `_run.cmd` — never hardcode a
  venv path in a script.

## File output (HARD rule)
- ALL file writes (temp files, outputs, scripts, artifacts) go to `workspace/tmp/`. Never
  `/tmp/`, `~`, or outside the repo.
- `workspace/tmp/` is ephemeral: delete what you create. Persisted outputs go to
  `workspace/<area>/`.

## Out of scope here
- TSDB/Chunk/Marquee data-access patterns and the ML Key Constraints (AGENTS.md) are
  src/-scoped. Load `memory/ref/python-tsdb.md` only if a helper genuinely touches market data.
