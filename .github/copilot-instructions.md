# Critical Rules (HARD — zero exceptions)

These rules apply to ALL agents in ALL modes. Violating any of them breaks automation or produces incorrect results. Full policy: see `AGENTS.md`.

---

## 1. File Output: `workspace/tmp/` Only

ALL file writes (temp files, outputs, scripts, artifacts) MUST go to `workspace/tmp/` relative to repo root.

**NEVER** write to `/tmp/`, `~`, `/home/*/`, or any path outside this repository. Violations trigger manual approval prompts that block automation.

## 2. Python/CLI: ALWAYS Use `./vol`

**NEVER** run `python`, `pytest`, `pip`, `uv`, or `mypy` directly — they will fail silently (wrong venv, missing LD_LIBRARY_PATH, broken nix deps). The `./vol` wrapper handles everything.

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

## 3. Terminal Isolation

Run ALL commands via `./vol exec` or `./vol bg`. **NEVER** run compute commands directly in the terminal.

- **NEVER** trust terminal buffer output — always `read_file` on the OUTPUT_FILE path.
- **ALWAYS** use `isBackground=true` for every `run_in_terminal` call.
- **NEVER** use `setsid`, `nohup`, `&`, `disown`, or any manual signal-isolation trick. The vol wrappers handle this correctly.
- If you see "terminal is blocked" or KeyboardInterrupt — use `./vol exec`. Do NOT retry.

## 4. Terminal Cleanup (EXIT GATE)

**Before returning your final response**, you MUST `kill_terminal` for every background terminal you spawned. Track every terminal ID. A subagent that returns without killing its terminals is FAILED.

## 5. Test-First (TDD)

Write a **failing test BEFORE implementation** for all Python code changes:
- New features → test defines expected behavior → implement minimum to pass
- Bug fixes → test reproduces the symptom → confirm it fails → fix
- Refactors → run existing tests as baseline → add characterization tests → restructure

Non-code files (config, docs, memory, YAML) are exempt.

## 6. Lint Gate (DISABLED)

~~Run `./vol lint` after every code change.~~ Lint is NOT required after every change. Only run lint when explicitly requested by the user or before a PR/commit.

## 7. Evidence Over Assumption

- Verify completion with actual command output or file contents.
- No fabrication. If a file, symbol, or API cannot be found, say so — never invent.
- Never claim "done" without verification evidence.

## 8. No Bare Tool Invocations

| NEVER do this | Do this instead |
|---------------|-----------------|
| `python script.py` | `./vol shell script.py` |
| `pytest tests/` | `./vol test` or `./vol exec pytest tests/` |
| `pip install X` | `./vol sync` (after adding to pyproject.toml) |
| `uv run python ...` | `./vol shell ...` or `./vol exec python ...` |
| `mypy volforecast/` | `./vol typecheck` |
| `ruff check .` | `./vol lint` |
## 9. Subagent Model Pinning

**All subagents MUST use Claude Opus 4.6.** Never spawn a subagent on a weaker model (Sonnet, Haiku, GPT, etc.). This is non-negotiable — weaker models miss edge cases, hallucinate APIs, and produce subtly wrong code that wastes debugging time.

When spawning subagents for context isolation (see `policy/context-isolation.md`), always include the context packet schema from `policy/subagent_protocol.md`. Subagents spawned from /plan, /execute, /research, /refactor have depth limit = 1 (they do NOT spawn further subagents).
---

**Full rules:** `AGENTS.md` · **CLI help:** `./vol help`
