# Critical Rules (HARD — zero exceptions)

These rules apply to ALL agents in ALL modes. Violating any of them breaks automation or produces incorrect results. Full policy: see `AGENTS.md`.

**Session boot:** execute the Boot Protocol in `AGENTS.md` (§Context Loading) before substantive work.
If this file is the only instruction file injected in your surface, read `AGENTS.md` first — nothing is auto-injected beyond these rules.

**Execution surfaces:** exactly two are supported — S-A (GS Windows desktop, VS Code Chat) and
S-B (GS Linux Coder workspace). The GitHub cloud coding agent (S-C) is **UNSUPPORTED**: `*.gs.com`
services are unreachable from cloud runners, `./vol` hard-exits there, and no `run_task` labels
resolve. Surface definitions: `AGENTS.md` → Supported Execution Surfaces.

---

## 1. File Output: `workspace/tmp/` Only

ALL file writes (temp files, outputs, scripts, artifacts) MUST go to `workspace/tmp/` relative to repo root.

**NEVER** write to `/tmp/`, `~`, `/home/*/`, or any path outside this repository. Violations trigger manual approval prompts that block automation.

**Scratch scripts:** prefer inline execution for one-off commands. A helper script for a bounded job MAY be written to `workspace/tmp/` — delete anything you create there after use. Persisted outputs go to `workspace/<area>/` (research, docs, configs), never to `tmp/`. This is the single tmp/-policy; no other file restates it.

## 2. Python/CLI: Use the Surface's Wrapper — Never Bare Tools
Surfaces per `AGENTS.md` → Supported Execution Surfaces.
- **S-B (Linux Coder):** ALWAYS use `./vol` (`shell|test|lint|fmt|exec|bg|sync`). **NEVER** run
  `python`, `pytest`, `pip`, `uv`, `ruff`, or `mypy` directly — they fail silently (wrong venv,
  missing LD_LIBRARY_PATH, broken nix deps).
- **S-A (GS Windows):** use `vol.cmd`/`run_task` equivalents once the Windows shim lands
  (until then, S-A tasks are doc/config-only or routed to S-B). `./vol` is bash-only and does
  not run on Windows.
- **S-C:** unsupported — do not dispatch compute here.

*(S-B forms; S-A equivalents arrive with `vol.cmd`.)*

| Command | Purpose |
|---------|---------|
| `./vol shell script.py` | Run Python script with correct env + `volforecast` importable |
| `./vol test -x -q -k name` | Run pytest (all args forwarded) |
| `./vol lint` | Ruff check (read-only) |
| `./vol fmt` | Ruff format (auto-fix) |
| `./vol exec <cmd>` | Signal-isolated blocking execution — read the OUTPUT_FILE it prints |
| `./vol bg <cmd>` | Fire-and-forget detached — poll OUTPUT_FILE for `EXIT_CODE=` sentinel |
| `./vol sync` | Install/update deps (NEVER `pip install` or `uv add` directly) |
| `./vol help` | Full command reference |

## 3. Terminal Isolation (both supported surfaces)
- **S-B:** run ALL compute via `./vol exec` or `./vol bg`. **NEVER** run compute commands
  directly in the terminal.
- **S-A:** run compute via the predefined VS Code tasks (their wrappers write the same
  `OUTPUT_FILE=` sentinel). Where no task exists and `vol.cmd` has not landed, the session is
  doc/config-only or routes compute to S-B.
- **NEVER** trust terminal buffer output — always `read_file` on the OUTPUT_FILE path.
- **ALWAYS** use `isBackground=true` for every `run_in_terminal` call.
- **NEVER** use `setsid`, `nohup`, `&`, `disown`, or any manual signal-isolation trick.
- If you see "terminal is blocked" or KeyboardInterrupt — use `./vol exec` (S-B). Do NOT retry.

## 4. Terminal Cleanup (EXIT GATE)

**Before returning your final response**, you MUST `kill_terminal` for every background terminal you spawned. Track every terminal ID. A subagent that returns without killing its terminals is FAILED.

## 5. Test-First (TDD)

Write a **failing test BEFORE implementation** for all Python code changes:
- New features → test defines expected behavior → implement minimum to pass
- Bug fixes → test reproduces the symptom → confirm it fails → fix
- Refactors → run existing tests as baseline → add characterization tests → restructure

Non-code files (config, docs, memory, YAML) are exempt.

## 6. Lint Gate (on request or pre-commit/PR)

Run `./vol lint` (S-B) / `vol.cmd lint` (S-A) **only** when explicitly requested by the user or before a PR/commit. Lint is NOT required after every change. The pre-commit hook (`workspace/lint/`, Plan 04) is the enforcement point at commit time. This is the single lint policy — `policy/working-agreements.md` and the workflows defer to this rule.

## 7. Evidence Over Assumption

- Verify completion with actual command output or file contents.
- No fabrication. If a file, symbol, or API cannot be found, say so — never invent.
- Never claim "done" without verification evidence.

## 8. No Bare Tool Invocations (per-surface wrappers)

Applies on both supported surfaces; the right-hand forms are S-B's — on S-A use the predefined task / `vol.cmd` equivalent once it lands.

| NEVER do this | Do this instead |
|---------------|-----------------|
| `python script.py` | `./vol shell script.py` |
| `pytest tests/` | `./vol test` or `./vol exec pytest tests/` |
| `pip install X` | `./vol sync` (after adding to pyproject.toml) |
| `uv run python ...` | `./vol shell ...` or `./vol exec python ...` |
| `mypy volforecast/` | `./vol typecheck` |
| `ruff check .` | `./vol lint` |
## 9. Subagent Model Pinning

Prefer **Claude Opus 4.6** for every subagent (the model-picker display name; this exact string is `EXPECTED_MODEL` in `workspace/lint/lint_model_pins.py`). **Fallback:** if it is not selectable in the current environment, use the strongest available Claude model, record the substitution in the return contract's `notes`, and never downgrade to a small/short-context model (Haiku-class). Canonical statement, depth limits (workflows = 1, /team = 2), and max concurrency (6): `policy/subagent_protocol.md`. When spawning subagents, always include the context packet schema from `policy/subagent_protocol.md`.
---

**Full rules:** `AGENTS.md` · **CLI help:** `./vol help`
