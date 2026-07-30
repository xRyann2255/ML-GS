# Implementation Boundary

What is implemented, what is design-goal only, and prerequisites for promotion.

Subordinate to AGENTS.md.

---

## Status Definitions

| Status | Meaning |
|--------|---------|
| **Implemented** | Operational — code/config exists, tested, relied upon |
| **Design Goal** | Specified in docs but not yet built. Agent must not assume it works. |
| **Deferred** | Considered and intentionally postponed. Revisit trigger documented. |

---

## Implemented (operational)

| Capability | Location | Notes |
|------------|----------|-------|
| CoALA memory system | `memory/` | Flat-file, frontmatter-validated |
| Skill system (54 skills) | `skills/` | AI_SLOP_CLEANER, BACKTEST, CANVAS, CONFLUENCE, CVS, DATA_AUDIT, DATA_INGEST, DIRGET, ENGHUB, ETASK, EVALUATE, FEATURE_BUILD, FORWARD_NETWORK, GIT, GIT_COMMIT, GITLAB_PIPELINES, GITLAB_SEARCH, GSSSO_AUTH, KILL_ORPHANS, MODEL_TRAIN, NDS_INFRA, NOTEBOOK, OUTLOOK, PDF_READER, PRIME_QUERY, PROCMON_JOBS, PROCMON_LOGS, PYTHON_MARKET_DATA, PYTHON_PATH, RESEARCH, SEARCH, SECDB_DIFF, SECDB_INSPECT, SECDB_POSITION, SECDB_TRANSLOG, SLANG_CLEANUP, SLANG_COPILOT, SLANG_EDIT, SLANG_EVAL, SLANG_GLIMPSE, SLANG_LINT, SLANG_READ, SLANG_REGTEST_FIX, SLANG_REVIEW, SLANG_REVIEW_INSPECT, SLANG_TEST_COVERAGE, SYMPHONY, TMD, expand-learning-graph, learning-status, quiz, study, teach, weekly-learning-goals |
| Slang cleanup skill | `skills/SLANG_CLEANUP/SKILL.md` | Best-practice + formatting passes |
| Persona registry (5 personas) | `personas/` | Capabilities and constraints defined |
| Execution protocol | `policy/execution_protocol.md` | Default execution flow, verification |
| Prompt-based activation | `.github/prompts/` | `#skill` and `#persona` prompt files |
| Output contract | `policy/output_contract.md` | Format-by-task, quality standards |
| Slang reference docs | `memory/slang/*.md` | Best practices, formatting, lint, run, headers |
| Slang editor + lint + review | `skills/SLANG_EDIT/`, `skills/SLANG_LINT/`, `skills/SLANG_REVIEW/` | `edit.py`, `lint.py`, `review.py` (all `secexpr --safe`) |
| Memory validation script | `workspace/lint/validate_memory.py` | Enforces meta/guide.md validation rules |
| Subagent coordination | `policy/subagent_protocol.md` | Leader/worker rules, concurrency limits |
| Section-level design docs | `*/design.md` | 5 section design.md files (workflows, skills, memory, personas, policy) |
| Master design | `workspace/design.md` | System-wide SSoT; section rules delegated to section design.md files |

## Design Goals (not yet implemented)

*No outstanding design goals. All specified capabilities are implemented or deferred.*

---

## Hard Rules

### secexpr must always run with `--safe`

Every `secexpr` invocation the agent generates **must** include `--safe`.
No exceptions — writes (`UpdateSecurity`, `DeleteSecurity`, `SecDbNew`) work in safe mode.
All operations (reads, writes, creates, deletes, lint, inspect) use `--safe`.

### Never hardcode kerberos, UserDB paths, or Object DB names

All DB identifiers and user-specific paths must be resolved at runtime:

1. **User argument first** — if the user passes `--db`, `--source`, or similar, use it verbatim.
2. **`person/user.md` fallback** — read `kerberos`, `Slang DB`, and `SecDb Object DB (default)` from memory.
3. **Never embed literal values** like `SPGProdNYC RO`, `!NYC UserDBs!home!<kerberos>`, or `~<kerberos>!clean` in skill code, SKILL.md examples, or procedural docs.
4. **Env-var bridge** — Python scripts may read an env var (e.g. `SLANG_LINT_DB`) with the `person/user.md` value as fallback default.
5. **When in doubt, ask** — if the user hasn't specified a DB and the task is ambiguous (e.g. RO vs RW, prod vs scratch), ask before proceeding.

Examples and docs should use `<ObjectDB>`, `<Slang DB>`, `<kerberos>` placeholders and
note the resolution chain.

### Prompt files must NOT use `#file:`, traversal links, or markdown links to other prompts

VS Code's `prompts-diagnostics-provider` validates both `#file:` directives and markdown links in `.prompt.md` files. In a multi-root workspace, it cannot verify file existence through `../` traversal — all formats (`#file:../../X`, `#file:X`, `text`) produce false "not found" warnings. Additionally, markdown links to peer `.prompt.md` files (e.g. `[text](mr.prompt.md)`) may fail the provider's existence check even though the file exists in the same directory.

**Rule:** Prompt files (`.prompt.md`) must reference context files as backtick-text list items:
- **Correct:** `` - `personas/vol-researcher.md` ``, `` - `skills/CANVAS/SKILL.md` ``, `` - `.github/prompts/mr.prompt.md` ``
- **Wrong:** `#file:../../personas/vol-researcher.md`, `[personas/vol-researcher.md]\(../../personas/vol-researcher.md\)`, `[mr.prompt.md](mr.prompt.md)`

The agent reads backtick-referenced files on demand via `read_file`. Paths are workspace-root-relative (no `../`).

This applies to all `.prompt.md` files in `.github/prompts/`. Enforced by `lint_vscode_md.py` (`file-ref-in-prompt`, `traversal-link-in-prompt`, `prompt-link-in-prompt`) and `lint_broken_refs.py` (`#file-in-prompt`).

---

## Deferred

| Capability | Reason | Revisit When |
|------------|--------|-------------|
| Slang runtime debugging | Out of scope for agent tooling; requires live SecDb context | User requests it and provides execution environment access |
| CVS commit/tag workflows | Read-only policy is a safety constraint, not a gap | Explicit user request + approval workflow designed |
| Episodic memory usage | Promotion rules now defined; no incidents recorded yet | First error promotion or post-mortem triggers first episodic file |
| Session continuity | Ephemeral Copilot Chat sessions don't support cross-session state | Platform supports persistent state |
| Temp cleanup policy | 7/14/30-day TTL by file type — no runtime to enforce | Session continuity is implemented |
| Error→episodic promotion | Requires session lifecycle hooks | Session continuity is implemented |

---

## Promotion Criteria

To move a design goal to implemented:

1. Code or config exists and is functional.
2. At least one successful end-to-end test or manual verification.
3. The design-goal row is moved to the implemented table.
4. Any dependent documents are updated.
