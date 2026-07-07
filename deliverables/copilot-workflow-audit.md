# ML-GS Copilot agentic workflow: 84 verified findings

*Agentic Workflow Audit · GitHub Copilot Configuration*

A skeptical, evidence-backed review of the repository's always-on instructions, path-scoped rules, 34 slash prompts, 48 skills, a two-tier memory system, workflows, policies, personas, the `./vol` wrapper, and an 18-module self-lint suite — every finding cites `path:line` and survived adversarial verification.

- **Scope:** git-tracked root tree (378 agentic files)
- **Method:** 141-agent workflow
- **Pipeline:** 15 readers → 7 dimensions → merge → adversarial verify → gap-chase
- **Cost:** 6.5M tokens · 1,504 tool calls · 65 min
- **Excluded:** `ml-vol-estimator/` · `qr-decode/` (untracked snapshots)

| Severity | Count | Meaning |
|---|---|---|
| BLOCKER | 6 | broken · silent-failure · security |
| HIGH | 20 | broad context waste / quality defect |
| MEDIUM | 40 | meaningful, localized |
| LOW | 18 | polish |

*Executive summary*

The workflow is **ambitious and largely well-structured on paper** — a clean five-primitive framework (instructions, prompts, skills, memory, policy) with progressive-disclosure intent and a self-validating lint suite. But it is **broken in ways that fail silently**, and it has already leaked credentials. Of 84 verified findings, the dominant failure mode (28 of 84) is **“broken / silently non-functional”**: mandated commands that dead-end on nonexistent modules, references that rot invisibly because the linter that would catch them never runs, and two mutually-exclusive execution architectures both declared universal `HARD` rules. The single most urgent issue is not a design flaw at all — it is a **live secret in version control**.

1. **A live GS Confluence token is committed, and the whole internal-tooling snapshot is off-perimeter** — AW-01/AW-02 — `workspace/config/.env` is git-tracked (not gitignored) with a real `CONFLUENCE_PAT`; the tree also holds 34 internal `*.gs.com` endpoints, a second PAT, employee PII, and 8 skills that disable TLS verification while sending bearer secrets. Independently reproduced.
2. **The mandated compute path is unrunnable on two of its three surfaces** — AW-07/AW-05/AW-G9 — `./vol` is bash+nix (dead on Windows); the skill task layer is `H:\`/Windows-bound (dead on Linux); the Copilot coding agent has neither `copilot-setup-steps.yml` nor a `.vscode/tasks.json`, so 0% of the wrapper resolves there — yet every fallback is a `HARD`-rule violation.
3. **Governance is fiction: the lint gate never runs and the budget arithmetic is invented** — AW-21/AW-15/AW-12 — the 14-check config linter has no CI/pre-commit trigger and currently fails 3/14; `memory/INDEX.md` token estimates are up to 10.8× low so the loaded tier is 63% over its own 50k cap; ~51 skill→memory links rotted after a half-finished migration, invisible to the linter by design.

**Highest-leverage move.** Two tiers. **Immediate (incident):** revoke both PATs, `git rm --cached workspace/config/.env`, gitignore it, purge history — ~15 min, stops active exposure. **Highest-leverage design fix:** make `copilot-instructions.md` the single owner of the 9 `HARD` rules and fix the `INDEX.md` budget math — this cuts the per-session boot load from **~10,235 → ~7,500 tokens** (a compounding ~27% saving on *every* request) and removes the contradictions that make the always-on rules read as negotiable.

*Phase 0 · Context-cost map*

## What it costs to load

The number that compounds is the always-on budget — paid on every Copilot request. It is not just the two always-on files: `AGENTS.md`'s Boot Protocol unconditionally instructs three more reads every session.

.github/copilot-instructions.md1,011 t

AGENTS.md3,269 t

+ boot read: memory/person/user.md859 t

+ boot read: memory/research/project-state.md2,510 t

+ boot read: memory/INDEX.md2,586 t

Always-on per session~10,235 t

**Worst-case single edit.** Editing one `src/**/*.py` file adds `python.instructions.md` (3,083 t) — and because its `applyTo` is `**/*.{py,ipynb}`, that same 3,083 t attaches when editing a `skills/` or `workspace/lint/` helper where it can't apply (AW-19), ~21% of tracked `.py`.

**Overlap.** The two instruction globs (`**/*.py` and `workspace/configs/**`) are disjoint — no double-attach — but the two always-on files duplicate 5 rule blocks (AW-26) and have already drifted.

**Projected after top fixes:** demote the mis-tiered fat P1 boot reads and cut ~40% stale history from `project-state.md` (AW-15/AW-16) + dedup the always-on pair (AW-26) → **~7,500 t/session**, plus ~3,083 t saved on every non-`src` Python edit by scoping the glob.

### Inventory rollup — tracked agentic surface

Clean, non-overlapping byte sums measured directly from `git ls-files`. Always-on rows shaded. (Full per-artifact Table 0 — all 194 inventory rows — is in the collapsible below.)

| Artifact class | Files | Bytes | ~Tokens |
|---|---|---|---|
| copilot-instructions (always-on) | 1 | 4,044 | 1,011 |
| AGENTS.md (always-on) | 1 | 13,077 | 3,269 |
| memory (active) | 45 | 299,528 | 74,882 |
| path-scoped instructions | 2 | 25,523 | 6,380 |
| slash prompts | 34 | 38,146 | 9,536 |
| skills: SKILL.md files | 48 | 288,430 | 72,107 |
| skills: bundled scripts/refs | 139 | 1,220,166 | 305,041 |
| skill shared-infra | 8 | 12,437 | 3,109 |
| workflows | 18 | 99,892 | 24,973 |
| policy | 14 | 38,839 | 9,709 |
| personas | 7 | 19,473 | 4,868 |
| memory (_dormant) | 37 | 284,599 | 71,149 |
| lint suite | 18 | 189,351 | 47,337 |
| vol wrapper | 1 | 20,980 | 5,245 |
| VS Code workspace/settings | 2 | 21,176 | 5,294 |
| CI / config | 3 | 1,831 | 457 |
| Tracked agentic surface | 378 | 2,577,492 | 644,373 |

### Top-14 largest artifacts

| File | Type | Load trigger | Bytes | ~Tok |
|---|---|---|---|---|
| `memory/ (active tree, 45 files excl. _dormant)` | memory-root rollup | on-demand (via AGENTS.md boot + INDEX lookup) | 299,528 | 74,882 |
| `memory/research/ (25 files)` | research-cards rollup | mixed: 1 P0 always-on, 11 P1 on-cue, 10 P2, 3 P3 per INDEX | 156,075 | 39,019 |
| `memory/_dormant/slang/ (16 files, rollup)` | dormant memory subtree | on-demand | 140,442 | 35,111 |
| `memory/_dormant/ref/ (12 files, rollup)` | dormant memory subtree | on-demand | 88,072 | 22,018 |
| `memory/ref/ (12 files)` | tech-reference rollup | scoped:**/*.{py,ipynb} for the 3 python-* files (python.instructions.md:10-12); rest on-demand via INDEX | 79,422 | 19,856 |
| `workspace/lint/design_lint.py` | lint (Python) | on-demand | 56,760 | 14,190 |
| `memory/_dormant/sys/ (9 files, rollup)` | dormant memory subtree | on-demand | 56,085 | 14,021 |
| `memory/_dormant/slang/builtin-functions-ref.md` | dormant memory (reference list) | orphan | 43,620 | 10,905 |
| `memory/research/lgbm-pooled-lessons.md` | P1 lessons log (largest file) | on-demand (INDEX:48 'LightGBM tuning, pooled training, feature selection') | 38,454 | 9,614 |
| `memory/slang/ (3 files)` | slang-reference rollup | on-demand (slang.prompt.md:20-21; policy/preflight-gates.md:10-12) | 37,906 | 9,477 |
| `memory/ref/python-tsdb.md` | P1 API reference | scoped:**/*.{py,ipynb} (python.instructions.md:11) + INDEX:100 | 22,838 | 5,710 |
| `memory/_dormant/slang/regtest.md` | dormant memory (testing conventions) | on-demand | 22,597 | 5,649 |
| `vol` | bash CLI wrapper (agent orchestration glue) | on-demand | 20,980 | 5,245 |
| `ml-vol-estimator.code-workspace` | VS Code workspace (settings + ALL task definitions) | always-on IF opened via workspace file; otherwise inert | 20,964 | 5,241 |

### ▸ Full Table 0 — all 194 inventoried artifacts (scroll)

| File | Type | Load trigger | Bytes | ~Tok | Notes |
|---|---|---|---|---|---|
| `.gs-project.yml` | GS product metadata | orphan (no agentic role; nothing references it) | 125 | 31 | productGuid + name ml-vol-estimator + description. Inert for the agent workflow. |
| `.github/workflows/ci.yml` | GitHub Actions workflow | ci | 1,144 | 286 | lint+format+mypy+pytest in src/. Push trigger [main, develop] misses default branch master; deps come from GS-internal PyPI unreachable on public runners; gh run list shows 0 runs |
| `.github/workflows/ci.yml` | GitHub Actions workflow | ci | 1,144 | 286 | Runs ruff/ruff-format/mypy/pytest(cov>=30) in src/ ONLY. Never invokes workspace/lint. Push trigger [main, develop] misses the default branch (origin/HEAD -> master); develop doesn |
| `memory/research/project-state.md` | P0 boot file | always-on (AGENTS.md:56 boot step 2) | 10,038 | 2,510 | updated 2026-07-01, freshest file. Self-contradicts: 'LSTM research line reopened' (l.15) vs 'LSTM research line CLOSED (2026-06-22)' (l.84); 'Blocker: None' (l.21) vs 'BLOCKER — b |
| `memory/person/ (user.md)` | P0 profile rollup | always-on (AGENTS.md:55 boot step 1) | 3,437 | 859 | User profile w/ Kerberos id, tone rules. updated 2026-04-07 (oldest P0). INDEX claims 280 tok, actual ~859. |
| `memory/ref/python-tsdb.md` | P1 API reference | scoped:**/*.{py,ipynb} (python.instructions.md:11) + INDEX:100 | 22,838 | 5,710 | 514 lines vs ref<=250 cap. ~300 lines are a raw TSDB field-dictionary dump. All examples Brazil (eq1d_brazil__tsdb, PETR4.SA, BRL_CDI) — off-universe for this project. |
| `memory/ref/python-chunk.md` | P1 API reference | scoped:**/*.{py,ipynb} (python.instructions.md:12) + INDEX:101 | 12,016 | 3,004 | 333 lines vs ref<=250 cap. Brazil examples (America/Sao_Paulo, WINJ25, DIJF26) in a US-equity/E-mini project. |
| `memory/research/lgbm-pooled-lessons.md` | P1 lessons log (largest file) | on-demand (INDEX:48 'LightGBM tuning, pooled training, feature selection') | 38,454 | 9,614 | 643 lines. Append-only growth with three RETRACTED sections preserved inline (lines 516-542, 559-573). INDEX claims 890 tok — 10.8x understatement. |
| `memory/research/qlike-defense.md` | P1 rationale doc | on-demand (INDEX:49 'QLIKE rationale, loss function choice') | 11,978 | 2,995 | 254 lines structured as saved Q&A ('## Prompt 1: ...') — transcript-shaped, brushing design.md rule 4 'no full transcripts'. Content itself is sound and project-critical. |
| `memory/slang/best-practices.md` | P1 slang style ref | on-demand (INDEX:85; slang.prompt.md:20) | 12,968 | 3,242 | 263 lines, within cap. Line 15 delegates RegTest/FasTest to _dormant/slang/regtest.md (active file depending on dormant content). |
| `memory/slang/lint-edit.md` | P1 slang tooling ref | on-demand (INDEX:87; preflight-gates.md:12) | 16,575 | 4,144 | 293 lines, within cap. Dense, high-quality operational knowledge (secexpr --safe, edit escalation ladder, colon-filename VFS workaround). Windows-specific assumptions explicit. |
| `memory/research/implied-vol.md` | P2 feature card | on-demand (INDEX:66 'Layer 2, options features, VRP signal') | 11,688 | 2,922 | 208 lines, updated 2026-06-11. Good status-table hygiene (resolved blockers marked in place). P2 so exempt from caps. |
| `memory/research/layer01-gap-analysis.md` | P2 gap analysis | on-demand (INDEX:60 'Layer 0-1 implementation, feature gaps') | 12,295 | 3,074 | Line 13: 'Archived 2026-05-11: All 9 gaps below are now implemented'. Historical-only per guide.md status table, yet INDEX still routes implementation work to it. |
| `memory/research/weekly-progress.md` | P3 pointer card | on-demand (INDEX:77) | 639 | 160 | 17-line pointer to workspace/research/weekly-progress.md (35,466 B, live). AGENTS.md:86 routes progress-log writes directly to the workspace file, bypassing this card. updated 2026 |
| `.vscode/settings.json` | VS Code folder settings | always-on (editor config, not model context) | 212 | 53 | Enables chat.promptFiles (prompt-file loading), pins copilot-chat extension affinity. 'chat.experimental.offerSetup' is a likely-obsolete key (HYPOTHESIS). Much thinner than the tr |
| `workspace/lint/lint_task.sh` | VS Code task wrapper (bash) | on-demand | 210 | 53 | Linux twin of lint_task.cmd; delegates to skills/_shared/_run.sh which DOES fall back to src/.venv then python3/python — asymmetric robustness vs the .cmd path. |
| `workspace/lint/lint_task.cmd` | VS Code task wrapper (batch) | on-demand | 112 | 28 | 3-line wrapper: sets _PY_SCRIPT=lint_all.py, _SKILL=LINT, delegates to skills/_shared/_run.cmd. Broken on this machine: _run.cmd requires H:\venv*\Scripts\python.exe (verified abse |
| `ml-vol-estimator.code-workspace` | VS Code workspace (settings + ALL task definitions) | always-on IF opened via workspace file; otherwise inert | 20,964 | 5,241 | Sole home of the 18 run_task tasks the workflow depends on (no .vscode/tasks.json). Also sets commandAllowlist terminal:['*'] and additionalReadAccessPaths h:/. Includes GS-only sl |
| `AGENTS.md` | agent instructions (always-on for coding agent / recent VS Code) | always-on | 13,077 | 3,269 | Project identity, boot protocol (3 mandatory reads + handoff check), subagent-first policy, constraints tables, skills registry, env section (Linux/Coder/nix). All 21 referenced pa |
| `skills/design.md` | architecture contract | on-demand | 5,506 | 1,377 | Skill-primitive contract: UPPER_SNAKE dirs, SKILL.md required with frontmatter (name, description), Skill Identity table, When to Use, Procedures; src/ scripts write to workspace/t |
| `vol` | bash CLI wrapper (agent orchestration glue) | on-demand | 20,980 | 5,245 | 33-command dispatch (vol:81-416). Never loaded as context itself, but copilot-instructions.md:13-35 mandates it for ALL agents; its help text (~4.6KB, vol:83-210) enters context wh |
| `.github/copilot-instructions.md` | copilot custom instructions | always-on | 4,044 | 1,011 | 9 'Critical Rules (HARD)': workspace/tmp-only writes, ./vol wrapper mandate, terminal isolation, kill_terminal exit gate, TDD, model pinning. Rule 6 is a struck-through DISABLED to |
| `.github/instructions/yaml-config.instructions.md` | copilot path-scoped instructions | scoped:workspace/configs/** | 13,190 | 3,298 | Experiment-config schema reference: required/optional fields, enum tables, ordering constraints, canonical-example maintenance rule. Glob matches exactly the 57 tracked workspace/c |
| `.github/instructions/python.instructions.md` | copilot path-scoped instructions | scoped:**/*.{py,ipynb} | 12,333 | 3,083 | Python env, GS data-access APIs, ML constraints (QLIKE/purged CV/COVID), TDD pointer, file-output rule. Glob matches all 349 tracked .py (0 tracked .ipynb). Contains stale import p |
| `skills/design.md` | design contract | on-demand | 5,506 | 1,377 | Skill-layer contract: frontmatter, Skill Identity, size lints (WARN>=250/ERROR>=400 lines), anti-patterns. All 9 audited skills satisfy frontmatter+Identity+When-to-Use; SLANG_REVI |
| `personas/design.md` | design-spec (meta, not a persona) | on-demand (cure.md DIAGNOSE loads it) | 5,121 | 1,280 | Design rules for the persona primitive. Rule §4.5 (line 49) names 8 personas that no longer exist (ANALYST, ORACLE, DOCTOR, SCRIBE, PATHFINDER, AUDITOR, PRESCRIBER, QUARTERMASTER-a |
| `workflows/design.md` | design-spec (meta, not a workflow) | on-demand (cure.md DIAGNOSE loads it) | 5,146 | 1,287 | Design rules for the workflow primitive. Correctly absent from INDEX.md registry (not dispatchable) — not an orphan; reachable only through cure.md. |
| `memory/_dormant/sys/etask.md` | dormant memory (API reference) | on-demand | 12,649 | 3,162 | eTask WFE gateway endpoints, PACT payloads, reasonCode tables, network constraints. Live dep of skills/ETASK/SKILL.md:52 (correct _dormant path) — but SKILL.md:48,229 also cite the |
| `memory/_dormant/ref/design-cure-patterns.md` | dormant memory (audit accelerator) | orphan | 15,560 | 3,890 | 33 recurring gap types + false-positive watch + lint-gap table for the ACTIVE /cure workflow ('Use this to accelerate future audits'). workflows/cure.md never references it; only r |
| `memory/_dormant/ref/web-server-auth.md` | dormant memory (auth implementation) | orphan | 13,752 | 3,438 | GSId/GSSSO cookie binary format + parser + OIDC/SSO-popup flows for workspace/create_eod_dashboard.py. No committed secrets (formats/code only); exposes owner kerberos '{kerberos}' (li |
| `memory/_dormant/ref/confluence-auth.md` | dormant memory (auth reference) | on-demand | 3,700 | 925 | PAT setup/BOM troubleshooting. Referenced in-place by skills/CONFLUENCE/SKILL.md:42. No committed secrets (placeholders only). Ironically its own anti-pattern table (line 76) forbi |
| `memory/_dormant/ref/gssso-auth.md` | dormant memory (auth reference) | on-demand | 3,194 | 799 | GSSSO cookie acquisition via SPNEGO. Referenced in-place by skills/GSSSO_AUTH:61, CANVAS:32, GITLAB_PIPELINES:37. CONTAINS COMMITTED CONFLUENCE PAT at line 87 (see findings). |
| `memory/_dormant/slang/language.md` | dormant memory (language reference) | orphan | 15,106 | 3,777 | Slang types/operators/scopes/functions/typed-structures, distilled from EngHub secdb-platform-docs. 'No Function Overriding' section duplicated near-verbatim in active memory/slang |
| `memory/_dormant/sys/secdb.md` | dormant memory (platform overview) | orphan | 11,654 | 2,914 | SecDB architecture (rings, eventual consistency, UFOs/VTs, Procmon, naming) written in Portuguese. Malformed frontmatter: dangling '- sys/enghub.md' under 'source:' with no relates |
| `memory/_dormant/slang/builtin-functions-ref.md` | dormant memory (reference list) | orphan | 43,620 | 10,905 | 609 curated Slang builtins (of ~44,500), one-liner each, 24 categories. Largest dormant file. Referenced only by sibling _dormant/slang/builtin-functions.md relates: — no skill/pro |
| `memory/_dormant/slang/syntax.md` | dormant memory (syntax gotchas) | orphan | 14,149 | 3,537 | Syntax patterns/anti-patterns for AI codegen (ternary, $-strings, Typecase, Finally). Marked IMMUTABLE via HTML comment. Oldest file (created 2025-07-14). No inbound refs from skil |
| `memory/_dormant/slang/regtest.md` | dormant memory (testing conventions) | on-demand | 22,597 | 5,649 | RegTest stubs/mocks/FasTest lifecycle, extracted from slang/best-practices.md. Live dep: best-practices.md:15 defers to it ('See _dormant/slang/regtest.md'). SLANG_TEST_COVERAGE ci |
| `memory/_dormant/slang/ (16 files, rollup)` | dormant memory subtree | on-demand | 140,442 | 35,111 | Slang language/testing/tooling reference. 5 files referenced in-place by active skills/memory; rest orphaned. All say status:active. 2 marked immutable:true (syntax.md, regtest.md) |
| `memory/_dormant/ref/ (12 files, rollup)` | dormant memory subtree | on-demand | 88,072 | 22,018 | SecDB graph/trade/PnL refs + auth refs (gssso, confluence, web-server) + slop-smells + forward-network. slop-smells.md and gssso-auth.md referenced in-place by 4 skills. Contains c |
| `memory/_dormant/sys/ (9 files, rollup)` | dormant memory subtree | on-demand | 56,085 | 14,021 | GS systems knowledge: etask, secdb, idea-jsi, enghub, ecs-obs, canvas, forward-networks. etask.md referenced in-place by skills/ETASK. secdb.md is Portuguese-language draft with br |
| `memory/meta/ (guide.md + skill-usage.md)` | governance rollup | on-demand (AGENTS.md:134 'loaded only when writing/validating memory files') | 7,587 | 1,897 | guide.md = naming/frontmatter/status spec (updated 2026-04-16). Contains NO 'Hard Gates' section despite AGENTS.md:153 and policy/working-agreements.md:11 citing one. No size guida |
| `workspace/lint/design_lint.py` | lint (Python) | on-demand | 56,760 | 14,190 | 26 architectural checks on personas/workflows/policy/skills/memory (sizes, purity, INDEX coverage, state machines, broken links). Currently FAILS: structural ERRORs on untracked ml |
| `workspace/lint/lint_broken_refs.py` | lint (Python) | on-demand | 19,600 | 4,900 | Cross-ref integrity: md links, #file: directives, backtick refs, frontmatter relates:. Currently FAILS on 2 tracked files: AGENTS.md:58 and gsvivs-audit.prompt.md:155. Overlaps des |
| `workspace/lint/lint_vscode_md.py` | lint (Python) | on-demand | 18,507 | 4,627 | Mojibake, #file: misuse, broken/relative/anchor links, SKILL.md frontmatter attrs, prompt cross-refs; --fix rewrites files. Currently FAILS — but every ERROR is in untracked dirs ( |
| `workspace/lint/validate_skills.py` | lint (Python) | on-demand | 13,623 | 3,406 | SKILL.md content: frontmatter name/description, H1 format, Purpose blockquote, Identity table, required sections, memory-link depth/targets, phantom paths; --fix rewrites links. PA |
| `workspace/lint/validate_memory.py` | lint (Python) | on-demand | 11,744 | 2,936 | CoALA memory schema: frontmatter fields, status enum, date order, naming, domain whitelist, relates: resolution, trust gates, P0+P1<=50k / P2<=100k token budgets (lines*5). PASSES |
| `workspace/lint/lint_hardcoded_env.py` | lint (Python) | on-demand | 9,030 | 2,258 | No hardcoded kerberos IDs (reads memory/person/user.md + USERNAME env) or GS DB names/paths in skill/lint .py files. Supports --fix (suggestions only, no writes). PASSES. |
| `workspace/lint/lint_vscode_tasks.py` | lint (Python) | on-demand | 8,649 | 2,162 | Validates tasks in ml-vol-estimator.code-workspace (NOT .vscode/tasks.json — none exists; tasks live in the tracked .code-workspace, 43 tasks). T1-T8 presentation/label rules + W/B |
| `workspace/lint/lint_memory_priority.py` | lint (Python) | on-demand | 8,020 | 2,005 | P0 token cap (800) + P1 reachability from skills/personas/prompts/AGENTS.md. Reachability uses bare substring stem match (line 100-102) so it is nearly vacuous; WARN-only, never fa |
| `workspace/lint/lint_skills_structure.py` | lint (Python) | on-demand | 6,807 | 1,702 | Skill folder layout: SKILL.md exact case, UPPER_SNAKE_CASE dirs, only SKILL.md+src/ at root, src/ content whitelist, skills/INDEX.md present. PASSES. |
| `workspace/lint/lint_forbidden_patterns.py` | lint (Python) | on-demand | 6,428 | 1,607 | Bans ssh/scp/sftp invocations and internal infra name 'strucd' in .py/.sh/.md/.cmd across skills/personas/workflows/policy/memory/prompts. PASSES. |
| `workspace/lint/lint_doc_safety.py` | lint (Python) | on-demand | 5,893 | 1,473 | G3/G4: no hardcoded GS DB names ('!NYC_CoreData', 'SPGProdNYC RO') or 'secexpr --full' examples in .md docs, with whitelists. PASSES. |
| `workspace/lint/lint_secexpr_safety.py` | lint (Python) | on-demand | 5,036 | 1,259 | Enforces secexpr safe-by-default in skills/*.py: no '--full' or safe=False outside whitelist, no unsafe default in secexpr_util.py. PASSES (39 files). |
| `workspace/lint/lint_registry_drift.py` | lint (Python) | on-demand | 5,001 | 1,250 | Skill/persona counts+lists in policy/implementation_boundary.md must match skills/ and personas/ on disk. PASSES. |
| `workspace/lint/lint_memory_index_completeness.py` | lint (Python) | on-demand | 4,299 | 1,075 | memory/<domain>/*.md all listed in INDEX.md, lowercase names, no phantom INDEX entries. PASSES. Duplicates design_lint check 10. |
| `workspace/lint/lint_all.py` | lint-runner (Python) | on-demand | 9,615 | 2,404 | Orchestrates 14 lints in parallel (4 workers), --args-file JSON + --out-file tee for task-based invocation. --quick is a no-op (all 14 entries is_slow=False). subprocess timeout=12 |
| `memory/INDEX.md` | memory index | always-on (AGENTS.md:57 boot step 3) — but only on surfaces that inject AGENTS.md; invisible to plain copilot-instructions.md-only chat | 10,343 | 2,586 | Master lookup table, P0-P3 tiers. Missing entry for research/README.md; lists 2 nonexistent workspace files; token estimates off by up to 10x vs measured sizes. |
| `memory/design.md` | memory primitive design doc | on-demand (INDEX:17 'Writing/validating memory files') | 4,758 | 1,190 | Holds the actual hard rules: size caps (slang<=400, ref<=250, person<=100 lines), budgets (P0+P1<=50k tok), no-append-growth. Cap table omits the 'research' domain entirely. |
| `memory/ref/vol-cli.md` | memory reference doc (mirror of vol help) | on-demand | 3,755 | 939 | Claims 'This file mirrors ./vol help' (line 13) but documents only 19 of 33 commands; omits test-all, the mandated pre-commit gate (vol:98). Linked from AGENTS.md:214 as 'full refe |
| `memory/ (active tree, 45 files excl. _dormant)` | memory-root rollup | on-demand (via AGENTS.md boot + INDEX lookup) | 299,528 | 74,882 | CoALA memory store. 45 tracked files. Governance split between meta/guide.md (naming/frontmatter) and design.md (caps/budgets). |
| `memory/research/README.md` | orphan tier summary | on-demand (research.prompt.md:13 loads it explicitly) | 3,230 | 808 | Stale duplicate of INDEX for research/: claims 8 P1 / 9 P2 / 5 P3 cards and '~16,300 tokens grand total' (actual research dir ~39k tok); lists 3 files that don't exist (project-pla |
| `workspace/lint/__init__.py` | package marker | orphan | 17 | 4 | '# tools package' — nothing imports workspace.lint as a package; all scripts run via __main__. |
| `personas/model-builder.md` | persona | on-demand (prompt shim: execute, cure, learn, refactor, experiment, feature, fix it, lint-workspace) | 2,820 | 705 | ML executor; most-referenced persona (8 prompts). ML discipline block duplicates AGENTS.md:79-84 constraints. |
| `personas/vol-researcher.md` | persona | on-demand (prompt shim: research, feature) | 2,624 | 656 | Read-only RV analyst. Embeds data-constraint facts (L2=E-mini only, 34+1 symbols) that duplicate AGENTS.md Data Access table — violates personas/design.md rule 4.2 (no domain knowl |
| `personas/eval-sentinel.md` | persona | on-demand (prompt shim: review, backtest, fix it) | 2,337 | 584 | 3-stage eval watchdog. Stage-1 checklist restates AGENTS.md Key Constraints (log-RV, purged CV, QLIKE, COVID) — 3rd copy of the same rules. |
| `personas/tracehound.md` | persona | on-demand (prompt shim: debug, fix it) | 2,160 | 540 | Read-only debugger, 3-failure circuit breaker. Clean, no domain leakage. |
| `personas/budgeteer.md` | persona | on-demand (prompt shim: lightweight) | 1,889 | 472 | Minimal-context executor. References VS Code tool `get_errors` by name — env-coupled. |
| `personas/INDEX.md` | persona-registry | on-demand | 2,522 | 631 | Capability matrix + conflict rules for 5 live personas; documents 11 deleted/inlined personas. Pointed to by AGENTS.md:229 but nothing auto-loads it. |
| `policy/interaction_model.md` | policy (UX/continuation) | orphan | 3,032 | 758 | Zero references outside policy/. Continuation policy (sec 2) near-verbatim duplicates execution_protocol.md L14 including identical example sentence; sec 5 duplicated at AGENTS.md: |
| `policy/working-agreements.md` | policy (dev hygiene + TDD gate) | on-demand | 1,857 | 464 | Referenced by AGENTS.md:85 and .github/instructions/python.instructions.md:260. L9 'Run lint, typecheck, and tests after changes' directly contradicts copilot-instructions.md sec 6 |
| `policy/ml-constraints.md` | policy (domain ML rules) | orphan | 4,483 | 1,121 | Claims 'always active' (L3) but zero references outside policy/index.md. 6 of 8 rules restated one-line in AGENTS.md:79-84; the operative detail (purge window >= horizon, QLIKE for |
| `policy/execution_protocol.md` | policy (execution flow) | on-demand | 1,001 | 250 | Link-only ref: AGENTS.md:232 cross-ref table. Continuation paragraph duplicates interaction_model.md sec 2 verbatim incl. the 'Two approaches: A or B' example. L5 grammar: 'Do not |
| `policy/operating-principles.md` | policy (general principles) | orphan | 1,288 | 322 | Zero references outside policy/. Effectively 100% restated in AGENTS.md Policy Quick-Ref L145-158, making the file dead weight. L11 vs L12 create the tmp/ scripts contradiction mir |
| `policy/communication_protocol.md` | policy (handoff/escalation) | orphan | 1,200 | 300 | Zero references outside policy/. Escalation row 'Blocked after 2 attempts' duplicates interaction_model.md:27 and overlaps subagent_protocol.md Failure Handling; HITL triggers dupl |
| `policy/output_contract.md` | policy (response format) | on-demand | 1,169 | 292 | Link-only refs: AGENTS.md:233 cross-ref table, workflows/design.md:62. No instruction ever says to read it. 'No fabrication' bullet is the 4th copy of that rule (also operating-pri |
| `policy/preflight-gates.md` | policy (session-start gates) | orphan | 1,245 | 311 | Claims 'fire before any other logic. Never skip' (L3) but nothing loads it; only mention is a reverse note at memory/INDEX.md:81. Competes with AGENTS.md Boot Protocol (L52-63) whi |
| `policy/implementation_boundary.md` | policy (status registry + hard rules) | orphan | 6,392 | 1,598 | Zero references outside policy/. Skill count (54) and persona count (5) verified accurate. Hard rules (secexpr --safe, no hardcoded DBs, prompt-link ban) duplicated in preflight-ga |
| `policy/context-isolation.md` | policy (subagent context isolation) | on-demand | 5,566 | 1,392 | Referenced by AGENTS.md:34, copilot-instructions.md:74, workflows/execute.md:108, plan.md:77, refactor.md:89, INDEX.md:15. ~80% overlaps subagent_protocol.md (same thresholds, same |
| `policy/subagent_protocol.md` | policy (subagent rules + terminal isolation) | on-demand | 5,291 | 1,323 | Referenced by AGENTS.md:34, copilot-instructions.md:74, workflows/execute.md:35+106, INDEX.md:15. Terminal Isolation section (L81-91) near-duplicates copilot-instructions.md sectio |
| `policy/index.md` | policy index | on-demand | 1,857 | 464 | Reached only via AGENTS.md:143 link. Lists 12 of 13 sibling files — design.md missing. routing.md description stale ('classification pipeline prompt→keyword→pattern→effort'; actual |
| `policy/routing.md` | policy stub (deprecated pointer) | on-demand | 212 | 53 | 5-line stub; its one rule is duplicated verbatim at always-on AGENTS.md:7. Inbound refs are stale: workflows/design.md:105 cites a nonexistent 'sec Step 5'; memory/_dormant cure-pa |
| `.pre-commit-config.yaml` | pre-commit config | ci (git hook; never referenced by any instruction file) | 562 | 141 | Pins ruff v0.4.4 and mypy v1.10.0 while src/uv.lock locks ruff 0.15.12 and mypy 2.0.0 — hooks will disagree with ./vol lint and CI. No instruction file tells agents pre-commit exis |
| `.github/prompts/gsvivs-audit.prompt.md` | prompt | on-demand | 6,824 | 1,706 | One-shot dated analysis task (context from '5 sample days 2022-05-25...') stored as a permanent slash command. Largest a-k prompt. 1 broken doc ref + 2 runtime-data refs absent in |
| `.github/prompts/slang-review.prompt.md` | prompt | on-demand | 6,227 | 1,557 | Largest l-z prompt. Auto-fill ScriptReview workflow. Step 2 writes lint args to the WRONG filename for the lint-slang task. Duplicates ~2KB of SLANG_REVIEW SKILL.md CLI templates. |
| `.github/prompts/lint-workspace.prompt.md` | prompt | on-demand | 2,671 | 668 | Workspace/repo lint suite. Its {run_id}-suffixed args filename is never read by the fixed-path lint-workspace task. 14-check list accurately maps to workspace/lint/*.py. |
| `.github/prompts/experiment.prompt.md` | prompt | on-demand | 2,371 | 593 | Two-mode protocol (new experiment / interpret) with validation gates and constraints; well designed. Line 18 refs pathless 'project-state.md' (memory/research/project-state.md exis |
| `.github/prompts/status.prompt.md` | prompt | on-demand | 1,848 | 462 | Read-only project dashboard. Line 29 references stale 'src/ml_vol_estimator/' (dir missing; renamed volforecast, correctly used at line 14). Output uses open-questions.md not liste |
| `.github/prompts/lint.prompt.md` | prompt | on-demand | 1,807 | 452 | Slang script lint. Contradicts the SLANG_LINT skill it mandates reading (run_task vs create_and_run_task; poll vs blocks-until-done). Duplicates skill's backend/status tables. |
| `.github/prompts/research.prompt.md` | prompt | on-demand | 1,609 | 402 | Research session with 7-step protocol; all 5 path refs + memory/INDEX.md exist; FEATURE_BUILD/DATA_INGEST skills exist. Well-formed. |
| `.github/prompts/feature.prompt.md` | prompt | on-demand | 1,572 | 393 | Feature-engineering mode with 7-layer taxonomy inline. Refs 2 personas + memory/research/har-components.md (exist); names DATA_INGEST skill in prose (skills/DATA_INGEST/SKILL.md ex |
| `.github/prompts/backtest.prompt.md` | prompt | on-demand | 1,415 | 354 | P&L backtest mode. Inlines signal types + 7-step workflow that duplicates skills/BACKTEST/SKILL.md. Refs personas/eval-sentinel.md + 2 memory cards (all exist). |
| `.github/prompts/glimpse.prompt.md` | prompt | on-demand | 1,311 | 328 | Slang-DB search with flag cheatsheet + index selection; good design. Command template uses '${input}' inside a quoted CLI arg (line 13) and runs python directly via PYTHON_PATH-res |
| `.github/prompts/kill-orphans.prompt.md` | prompt | on-demand | 1,134 | 284 | Windows process cleanup with mandatory -DryRun preview; good safety design. Runs skills/KILL_ORPHANS/src/cleanup.ps1 directly in terminal (exists), which sits outside the './vol ex |
| `.github/prompts/slang.prompt.md` | prompt | on-demand | 1,080 | 270 | Slang context loader: 5 skills + 3 reference docs + key reminders (VFS-first). All 8 refs exist. Distinct from /slang-review, not a dup. |
| `.github/prompts/learning-status.prompt.md` | prompt | on-demand | 696 | 174 | Learning mastery dashboard. Line 8 runs 'python3 ...' directly, violating always-on ./vol rule; dispatches subagent for text summary. |
| `.github/prompts/study.prompt.md` | prompt | on-demand | 664 | 166 | Router between /teach and /quiz; deliberately loads all 3 learning skills + 3 state files. Intentional composition, not duplication. |
| `.github/prompts/teach.prompt.md` | prompt | on-demand | 647 | 162 | Teach mode; hands off to /quiz. All refs exist. Clean. |
| `.github/prompts/expand-learning-graph.prompt.md` | prompt | on-demand | 601 | 150 | Dispatches subagent to expand learning graph. Refs skills/expand-learning-graph.md (a loose .md skill, not SKILL.md dir pattern) + 2 workspace/learning files; all exist. Good argum |
| `.github/prompts/quiz.prompt.md` | prompt | on-demand | 597 | 149 | Interactive quiz mode; all 4 refs exist. Flat-file skill (skills/quiz.md) vs dir-style SKILL.md pattern elsewhere. |
| `.github/prompts/weekly-learning-goals.prompt.md` | prompt | on-demand | 499 | 125 | Weekly learning goals via subagent; all 4 refs exist. Clean. |
| `.github/prompts/plan.prompt.md` | prompt | on-demand | 484 | 121 | Planning mode; 2-sentence body + 1 bare path bullet. Clean. |
| `.github/prompts/progress.prompt.md` | prompt | on-demand | 410 | 103 | Weekly Confluence progress log. Distinct from /status (write vs read-only dashboard) but shares 2 of its source files. |
| `.github/prompts/fix it.prompt.md` | prompt | on-demand | 382 | 96 | Filename contains a space; no name: frontmatter override, so slash-command name derives from 'fix it' — likely uninvocable/collides with built-in /fix (see finding). Refs workflows |
| `.github/prompts/refactor.prompt.md` | prompt | on-demand | 342 | 86 | Refactor mode; 1 sentence + 2 path bullets. Clean. |
| `.github/prompts/review.prompt.md` | prompt | on-demand | 331 | 83 | Severity-rated review mode; 1 sentence + 2 path bullets. Clean. |
| `.github/prompts/debug.prompt.md` | prompt | on-demand | 324 | 81 | Dispatcher to workflows/debug.md + tracehound persona (both exist). Overlaps 'fix it' but descriptions differentiate (root-cause vs full fix pipeline). |
| `.github/prompts/team.prompt.md` | prompt | on-demand | 312 | 78 | Parallel subagent coordination; 1 sentence + 1 path bullet. Clean. |
| `.github/prompts/gitlab-search.prompt.md` | prompt | on-demand | 299 | 75 | Thin dispatcher to skills/GITLAB_SEARCH/SKILL.md (exists). Uses bare '${input}' (line 9). GS-internal GitLab dependency (env-bound by design). |
| `.github/prompts/git-commit.prompt.md` | prompt | on-demand | 297 | 74 | Thin dispatcher to skills/GIT_COMMIT/SKILL.md (exists). Uses bare '${input}' (line 9) — undocumented prompt-file variable (see finding). |
| `.github/prompts/execute.prompt.md` | prompt | on-demand | 287 | 72 | Dispatcher to workflows/execute.md + model-builder persona (both exist). Good description. |
| `.github/prompts/slop-cleaner.prompt.md` | prompt | on-demand | 206 | 52 | Body is a single bare path bullet to the skill; no instruction verb. |
| `.github/prompts/cure.prompt.md` | prompt | on-demand | 191 | 48 | Thin dispatcher to workflows/cure.md + persona. Name 'cure' opaque but description explains ('design-compliance healthcheck and remediation'). Refs exist. |
| `.github/prompts/data-audit.prompt.md` | prompt | on-demand | 191 | 48 | Clean thin dispatcher to skills/DATA_AUDIT/SKILL.md (exists). Good description. Model pattern for skill-backed prompts. |
| `.github/prompts/bootup.prompt.md` | prompt | on-demand | 180 | 45 | Body is a single bare bullet '- `workflows/bootup.md`' with no instruction verb. Description ('learn all capabilities, skills, memory') mismatches the workflow's actual behavior (l |
| `.github/prompts/lightweight.prompt.md` | prompt | on-demand | 176 | 44 | Budget mode. Body is only 2 bare path bullets, no verb. |
| `.github/prompts/learn.prompt.md` | prompt | on-demand | 161 | 40 | Body is ONLY 2 bare backtick path bullets, no instruction verb. Relies entirely on convention that agent reads listed paths. |
| `memory/research/ (25 files)` | research-cards rollup | mixed: 1 P0 always-on, 11 P1 on-cue, 10 P2, 3 P3 per INDEX | 156,075 | 39,019 | Distilled cards + logs for ML vol project. Contains orphan README.md, archived-but-indexed layer01-gap-analysis, month-stale research-journal, and the 38KB lgbm-pooled-lessons. |
| `policy/design.md` | section design doc (meta) | on-demand | 4,246 | 1,062 | Referenced only from workspace/design.md:28. NOT listed in policy/index.md — violates its own rule 4.1. Stale interfaces: claims referenced-by workflows/_protocol.md (zero 'policy' |
| `memory/research/research-journal.md` | session log | on-demand (INDEX:39 'Research session start, continuity') | 11,332 | 2,833 | Last entry 2026-06-03 — a month behind project-state (2026-07-01); trials 036-073 unjournaled despite line 13 'Read at start of every session for continuity'. Duplicates project-st |
| `workflows/_protocol.md` | shared workflow contract | on-demand (referenced by every workflow's first line) | 2,210 | 553 | Entry/exit/error/composition contract. Persona Quick-Reference table (lines 44-50) duplicates personas/INDEX.md Cannot-Do column so keyword-routed sessions never load persona files |
| `skills/_shared/gitlab_auth.py` | shared-infra (auth lib) | on-demand | 2,188 | 547 | No hardcoded secrets (PAT via git credential fill — good). But _ssl_ctx() sets CERT_NONE + check_hostname=False, then sends PRIVATE-TOKEN over that unverified channel. |
| `skills/_shared/nix_ld.sh` | shared-infra (env shim) | ci | 793 | 198 | Linux-only LD_LIBRARY_PATH setup for nix-store pythons. Guarded (no-op if LD_LIBRARY_PATH set or PY not nix). Sound; irrelevant on this Windows snapshot. |
| `skills/_shared/subprocess_utils.py` | shared-infra (subprocess lib) | on-demand | 2,186 | 547 | Cross-platform process-tree-kill-on-timeout run() replacement. Clean implementation (taskkill /T on win32, killpg elsewhere). No issues found. |
| `skills/_shared/_run.sh` | shared-infra (task bootstrap, Linux) | ci | 2,613 | 653 | Linux twin. Diverges: python from src/.venv\|python3 (not H:\venv*); args properly array-quoted ("${_ORIG_ARGS[@]}") unlike cmd %*; errors to stderr; sources nix_ld.sh. Also always |
| `skills/_shared/_run.cmd` | shared-infra (task bootstrap, Windows) | ci | 2,112 | 528 | Called by every *_task.cmd wrapper. Hard-depends on H:\all-languages-env.cmd + H:\venv315..38. Always exits 0 ('so VS Code close:true disposes the terminal') — bootstrap errors inv |
| `skills/_shared/usage_report.py` | shared-infra (telemetry report) | skill-manual | 1,402 | 351 | --since does lexical compare parts[0][:10] < 'YYYY-MM-DD'; works for ISO (.sh) lines only — Windows-format lines ('Tue007/01/...') always pass the filter ('T' > '2'). Nothing in tr |
| `skills/_shared/log_usage.cmd` | shared-infra (telemetry) | ci | 659 | 165 | Locale-dependent timestamp (%DATE%T%TIME%, spaces->0, e.g. 'Tue007/01/2026T23:34:00'). Appends to workspace/tmp/skill_usage.log — dir absent on fresh clone/this snapshot, so append |
| `skills/_shared/log_usage.sh` | shared-infra (telemetry) | ci | 484 | 121 | ISO timestamps (date -Iseconds) — format diverges from .cmd twin, breaking usage_report.py --since on mixed logs. Same silent no-op if workspace/tmp missing. |
| `skills/CANVAS/SKILL.md` | skill | on-demand (skills/INDEX.md; AGENTS.md:199 marks GS-infra skills as unused in project workflow) | 11,265 | 2,816 | Bundle 90156B (query.py 29348B, openapi.json 49237B, .cmd+.sh wrappers). 260 lines — exceeds design.md WARN>=250. ~70% is API endpoint reference tables (anti-pattern 1 'skill as kn |
| `skills/SLANG_REGTEST_FIX/SKILL.md` | skill | on-demand | 10,860 | 2,715 | Largest of the group (241 lines). Orchestrator skill (violates design.md boundary 'orchestration is a workflow concern' arguably). Rich troubleshooting table is genuinely procedura |
| `skills/OUTLOOK/SKILL.md` | skill | on-demand (skills/INDEX.md only) | 10,770 | 2,693 | Largest K-P skill (224 lines, near 250 WARN). No src/ — pure procedure doc, good progressive disclosure. Internally inconsistent memory links: line 29 uses _dormant path, Links sec |
| `skills/ETASK/SKILL.md (+src: etask.py 43255B, etask_task.cmd 103B, etask_task.sh 201B)` | skill | skill-manual | 10,043 | 2,511 | eTask Workflow Engine REST CLI (read+write: complete/cancel/archive tasks). Corrupted headings ('## CList Open Tasks', '### LI Commands'). Hardcodes kerberos '{kerberos}' 19x. etask.py |
| `skills/SLANG_REVIEW/SKILL.md` | skill | on-demand | 9,714 | 2,429 | 253 lines — breaches its own design-lint WARN threshold (>=250). Internal contradiction: 'blocks until done — no polling needed' (l.163) vs 'Use 60s poll intervals' (l.241). Links |
| `skills/SLANG_EDIT/SKILL.md` | skill | on-demand | 9,456 | 2,364 | VFS-first/secexpr-fallback CRUD; largest of the ten (249 lines, 1 under WARN=250). Bundled: edit.py 47283B, cmd 107B, sh 205B. Referenced by 3 prompt files + workflows dispatch. 3 |
| `skills/PYTHON_MARKET_DATA/SKILL.md` | skill | on-demand (AGENTS.md:188 + skills/INDEX.md) + scoped: .github/instructions/python.instructions.md (applyTo **/*.{py,ipynb}) line 16 tells model to read it | 8,565 | 2,141 | Doc-only skill (no src/) — decision tree + boilerplate, good progressive disclosure into 3 memory files (all exist). Duplicate section numbering: two '### 3.' headings (lines 110, |
| `skills/CONFLUENCE/SKILL.md` | skill | on-demand (skills/INDEX.md) | 8,460 | 2,115 | Bundle 29522B (client.py 20968B). Directs PAT storage in workspace/config/.env — that file is git-tracked WITH a live PAT. client.py defaults verify_ssl=False. Links cite memory/re |
| `skills/SECDB_TRANSLOG/SKILL.md` | skill | on-demand | 7,954 | 1,989 | PFOB transaction-log wrapper, list/diffs modes, InfiniteTransLogDb auto-resolution. Bundled: translog.py 22774B, cmd 115B, sh 213B. 'How It Works' has duplicate step numbering (two |
| `skills/SLANG_EVAL/SKILL.md` | skill | on-demand | 7,669 | 1,917 | JSON-RPC eval via VS Code extension SSP endpoint on 127.0.0.1. Bundled: eval.py 13193B, cmd 107B, sh 205B. Port auto-detect is PowerShell-only, so the shipped .sh wrapper can never |
| `skills/MODEL_TRAIN/SKILL.md` | skill | on-demand (AGENTS.md:183 core-skills table + skills/INDEX.md) | 7,288 | 1,822 | Core vol-project skill. BROKEN: wrapper invokes nonexistent module volforecast.models.train; real path is `vol run` CLI per memory/ref/vol-cli.md. Hardcodes workspaceFolder h:\ml-v |
| `skills/SECDB_DIFF/SKILL.md` | skill | on-demand | 7,266 | 1,817 | Instream diff of two securities; reuses SECDB_INSPECT parser. Bundled: diff.py 14851B, cmd 107B, sh 205B. Only SECDB_* skill with a workflows/INDEX.md dispatch keyword (line 57). M |
| `skills/FEATURE_BUILD/SKILL.md (+src: feature_task.cmd 954B, feature_task.sh 1718B)` | skill | skill-manual (named in always-on AGENTS.md skills table) | 7,063 | 1,766 | Feature layers 0-6 wrapper around python -m volforecast.features.build. 12 memory refs, all exist. Heavy formula tables inline but each layer also points to memory (borderline know |
| `skills/SLANG_LINT/SKILL.md` | skill | on-demand | 7,012 | 1,753 | Slang lint via secexpr wrapper. Referenced by lint.prompt.md and slang-review.prompt.md. SKILL.md instructs create_and_run_task with run_id-suffixed args files; predefined lint-sla |
| `skills/FORWARD_NETWORK/SKILL.md (+src: forward_network_api.yaml 485434B, fwd_api.py 5227B, fwd_api_task.cmd 115B, fwd_api_task.sh 213B)` | skill | skill-manual (AGENTS.md:199 declares GS-internal skills 'not used in this project's workflow') | 6,871 | 1,718 | Forward Networks API client (2 instances, Basic Auth token files under %USERPROFILE%). Bundles 485KB OpenAPI spec (~121K tokens). All 5 memory/ref/forward-network.md links dangle. |
| `skills/GIT/SKILL.md (+src: git_task.cmd 3136B, git_task.sh 3184B, mr_task.cmd 103B, mr_task.ps1 3310B, mr_task.py 4441B, mr_task.sh 201B, noop_editor.cmd 12B)` | skill | skill-manual (named in always-on AGENTS.md utility-skills table) | 6,693 | 1,673 | Zero-Allow git wrapper via run_task. Self-contradicts: full-push example uses ['add','-A'] while Conventions say NEVER git add -A. {run_id} args filename contradicts fixed task pat |
| `skills/GIT_COMMIT/SKILL.md (+src: commit_task.cmd 114B, commit_task.py 20675B, commit_task.sh 212B)` | skill | skill-manual + on-demand via .github/prompts/git-commit.prompt.md | 6,687 | 1,672 | Auto-group + conventional commit + push in one task run. Well-designed deny-list and grouping. Same {run_id} args-filename contradiction as GIT. Denied path 'workspace/docs/enghub/ |
| `skills/CVS/SKILL.md` | skill | on-demand (skills/INDEX.md) | 6,630 | 1,658 | Bundle 13085B (cvs.py 6159B + .cmd/.sh 3-line bootstrap wrappers via skills/_shared/_run.cmd). PowerShell-only CLI examples (Select-String/Select-Object) despite .sh wrapper existi |
| `skills/EVALUATE/SKILL.md (+src: eval_task.cmd 975B, eval_task.sh 1718B)` | skill | skill-manual (named in always-on AGENTS.md skills table) | 6,552 | 1,638 | Vol-model evaluation (QLIKE/DM/MCS) wrapper around python -m volforecast.evaluation.evaluate. All 5 memory refs exist. .cmd wrapper lacks stale-output cleanup/usage-log that .sh ha |
| `skills/SLANG_GLIMPSE/SKILL.md` | skill | on-demand | 6,526 | 1,632 | ELPS/Glimpse code search wrapper. Referenced by glimpse.prompt.md + slang.prompt.md. Self-inconsistent memory links (line 39 _dormant vs lines 114/166 non-dormant, latter missing). |
| `skills/RESEARCH/SKILL.md` | skill | on-demand | 6,441 | 1,610 | Agent-protocol research skill. Bundled: research_task.cmd 931B, research_task.sh 1714B. Task path broken end-to-end (nonexistent module, stub CLI). research.prompt.md re-implements |
| `skills/NOTEBOOK/SKILL.md` | skill | on-demand (AGENTS.md:187 core-skills table + skills/INDEX.md) | 6,084 | 1,521 | BROKEN twice: wrapper invokes nonexistent volforecast.pipeline.notebook (real module cli/notebook.py takes --config not --args-file); import boilerplate uses nonexistent package ml |
| `skills/DATA_AUDIT/SKILL.md` | skill | on-demand (via .github/prompts/data-audit.prompt.md + skills/INDEX.md) | 5,978 | 1,495 | Bundle = SKILL.md only (no src/; runs project CLI './vol audit'). References data/manifest.yaml which doesn't exist in tracked tree (src/data/ gitignored — generated at runtime, ac |
| `skills/BACKTEST/SKILL.md` | skill | on-demand (skills/INDEX.md; NOT referenced by backtest.prompt.md) | 5,778 | 1,445 | Bundle 8445B (SKILL.md + backtest_task.cmd 937B + backtest_task.sh 1730B; both OS variants exist). Task execution hardcodes workspaceFolder h:\ml-vol-estimator (line 134). Duplicat |
| `skills/PRIME_QUERY/SKILL.md` | skill | on-demand (skills/INDEX.md; only K-P skill with workflows/INDEX.md trigger keywords) | 5,747 | 1,437 | Internal GS endpoint, GSSSO cookie auth. prime.py:81-83 disables TLS verification (CERT_NONE) while sending the SSO cookie. Cookie obtained via PowerShell — Windows-only despite ba |
| `skills/SECDB_INSPECT/SKILL.md` | skill | on-demand | 5,697 | 1,424 | Instream VT inspection via DiskInstreamValues trace parsing; documents why trace parsing (4 failed alternatives). Bundled: inspect.py 16246B, cmd 113B, sh 211B. No inbound refs exc |
| `skills/TMD/SKILL.md` | skill | on-demand | 5,643 | 1,411 | ~60% inline API reference tables (endpoints, form IDs) — 'skill as knowledge store' per design.md anti-pattern 1. Hardcodes kerberos '{kerberos}' 7x. Links workspace/docs/tmd/ which do |
| `skills/GITLAB_SEARCH/SKILL.md (+src: gitlab-search.ps1 7517B, gitlab-search_task.cmd 119B, gitlab-search_task.sh 217B, gitlab_search.py 6595B)` | skill | skill-manual + on-demand via .github/prompts/gitlab-search.prompt.md | 5,592 | 1,398 | GitLab Search API (global/project/group). Clean JSON-args interface, but Output/Troubleshooting still cite legacy PS1 flags (-OutFile, -MaxResults). gitlab-search.ps1 is a full fun |
| `skills/SECDB_POSITION/SKILL.md` | skill | on-demand | 5,338 | 1,335 | Children()/DiddlePositions position sourcing. Bundled: position.py 14905B, cmd 115B, sh 213B. Embeds Slang pattern duplicated from now-dormant secdb-position-pnl.md; example hardco |
| `skills/DATA_INGEST/SKILL.md` | skill | on-demand (skills/INDEX.md) | 5,157 | 1,289 | Bundle 7820B (ingest_task.cmd 955B + ingest_task.sh 1708B, both OS variants). Hardcodes workspaceFolder h:\ml-vol-estimator (line 111). Embeds the 34-symbol universe inline (also i |
| `skills/SLANG_READ/SKILL.md` | skill | on-demand | 5,084 | 1,271 | VFS-first script reader; good progressive disclosure (defers to SLANG_EDIT/CVS). No src/ of its own. Links memory/slang/run.md which is missing (moved to _dormant). Hardcodes works |
| `skills/NDS_INFRA/SKILL.md` | skill | on-demand (skills/INDEX.md only; AGENTS.md:199 marks GS-internal skills unused for vol project) | 4,909 | 1,227 | Internal GS endpoint. Real employee PII in examples (kerberos, name, title, email, IP, hardware serial). Scope contradiction: dialtone 'out of scope' (line 10,33) yet documented+im |
| `skills/GITLAB_PIPELINES/SKILL.md (+src: fetch-pipeline.ps1 4064B, fetch_pipeline.py 4472B, gitlab-auth.ps1 4582B, lint-ci-yaml.ps1 2254B, lint_ci_yaml.py 2494B, pipelines_task.cmd 123B, pipelines_task.sh 221B)` | skill | skill-manual | 4,677 | 1,169 | Read-only pipeline/job inspection. Auth story contradictory: description says SSO/SAML, body says PAT-only. 3 legacy .ps1 (incl. full SAML flow) ship unreferenced by SKILL.md. lint |
| `skills/AI_SLOP_CLEANER/SKILL.md` | skill | on-demand (via .github/prompts/slop-cleaner.prompt.md + skills/INDEX.md) | 4,654 | 1,164 | 4-phase regression-locked cleanup procedure. Bundle = SKILL.md only (4654B, no src/). Links section cites memory/ref/slop-smells.md which is MISSING (moved to memory/_dormant/ref/) |
| `skills/KILL_ORPHANS/SKILL.md` | skill | on-demand (skills/INDEX.md registry) + slash prompt .github/prompts/kill-orphans.prompt.md | 4,421 | 1,105 | Destructive process killer. Troubleshooting section copy-pasted 3x (lines 77-96). Two parallel impls: cleanup.py 15892B (SKILL.md Tool field) and cleanup.ps1 9163B (prompt uses thi |
| `skills/SEARCH/SKILL.md` | skill | on-demand | 4,410 | 1,103 | Inverted-index search over skills/ and memory/. Bundled: search.py 16875B, cmd 105B, sh 203B (3-line shared-runner wrappers). CLI examples hardcode H:\venv311 and h:\ml-vol-estimat |
| `skills/PDF_READER/SKILL.md` | skill | on-demand (skills/INDEX.md only) | 4,146 | 1,037 | Clean, portable (pypdf, stdlib CLI). Integration example imports ConfluenceClient without showing sys.path setup. Task label pdf-reader exists in ml-vol-estimator.code-workspace:21 |
| `skills/ENGHUB/SKILL.md (+src: clone-all.sh 2772B, clone-one.sh 898B, enghub.py 8335B, enghub_task.cmd 105B, enghub_task.sh 203B, update-all.sh 684B)` | skill | skill-manual | 4,042 | 1,011 | Clone/search GS EngHub GitLab docs into workspace/knowledge/enghub/ (gitignored). Frontmatter OK. Repo list duplicated in clone-all.sh vs enghub.py and diverged. Registry memory li |
| `skills/DIRGET/SKILL.md` | skill | on-demand (skills/INDEX.md) | 3,812 | 953 | Bundle 17510B (dirget.py 13390B + .cmd/.sh wrappers). Routes to nonexistent skill 'APPDIR_API' (renamed CANVAS). Commits real employee kerberos IDs and names as examples. Links cit |
| `skills/SYMPHONY/SKILL.md` | skill | on-demand | 3,726 | 932 | Symphony chat reader. Both memory Links broken (files in memory/_dormant/ref/). Not referenced by any .github artifact; AGENTS.md l.199 declares GS-internal skills unused. Uses H:\ |
| `skills/PROCMON_JOBS/SKILL.md` | skill | on-demand (skills/INDEX.md; declared dependency skill for support skills) | 3,414 | 854 | OIDC/Kerberos/SPNEGO auth, needs curl.exe + kinit. Declares itself dependency of CPNL_SUPPORT which does not exist in skills/ — stale after skill removal. Bundled: fetch_process_li |
| `skills/PYTHON_PATH/SKILL.md` | skill | on-demand dependency — referenced by 10+ other SKILL.mds, skills/INDEX.md, and 2 prompts (glimpse.prompt.md, slang-review.prompt.md) | 3,195 | 799 | Dependency skill. resolve.py (4.9KB) bundled but never referenced by SKILL.md or any consumer — SKILL.md Tool field lists resolve.ps1 only. Hardcodes H:\venv* fallback/scan (resolv |
| `skills/SLANG_TEST_COVERAGE/SKILL.md` | skill | on-demand | 3,056 | 764 | EPSSP coverage fetcher. Args-file name in SKILL.md (epssp_coverage_args.json) does NOT match the predefined task's --args-file (slang_test_coverage_args.json) — task-based path alw |
| `skills/SLANG_CLEANUP/SKILL.md` | skill | on-demand | 3,054 | 764 | Pure-instruction pointer skill (no src/, no task) deferring to memory/slang/best-practices.md + formatting.md — best progressive-disclosure example of the ten. Both link targets ex |
| `skills/SLANG_COPILOT/SKILL.md` | skill | on-demand | 3,046 | 762 | Clones internal GitLab repo (gitlab.aws.site.gs.com) into workspace/docs/slang/. Bundled: copilot_setup.py 4277B, cmd 119B, sh 217B. Legacy bash section uses /tmp (non-Windows). la |
| `skills/SLANG_REVIEW_INSPECT/SKILL.md` | skill | on-demand | 2,745 | 686 | Compact, well-scoped validator. Reached only via SLANG_REVIEW SKILL.md ('After success, runs SLANG_REVIEW_INSPECT'). Links memory/slang/review.md (missing; in _dormant). Task label |
| `skills/PROCMON_LOGS/SKILL.md` | skill | on-demand (skills/INDEX.md only) | 2,632 | 658 | Only K-P executable skill with NO VS Code task (no label in ml-vol-estimator.code-workspace, no .cmd wrapper, no Task-Based Execution section) — bash-only fetch.sh on Windows-prima |
| `skills/GSSSO_AUTH/SKILL.md (+src: get-cookie.sh 1121B, get-cookie_task.cmd 1526B, get-cookie_task.sh 1343B)` | skill | skill-manual; declared dependency skill ('called by other skills, not directly') per design.md rule 10 — compliant | 2,608 | 652 | Kerberos/SPNEGO -> GSSSO cookie. Cookie (24h SSO credential) written plaintext to workspace/tmp/gssso_cookie.txt, which is NOT gitignored. Wrapper always exits 0; failure detectabl |
| `memory/slang/ (3 files)` | slang-reference rollup | on-demand (slang.prompt.md:20-21; policy/preflight-gates.md:10-12) | 37,906 | 9,477 | Well-distilled, policy-protected (INDEX:81 claim verified vs preflight-gates.md:10-12). All within 400-line slang cap. best-practices.md:15 points into memory/_dormant/slang/regtes |
| `memory/ref/ (12 files)` | tech-reference rollup | scoped:**/*.{py,ipynb} for the 3 python-* files (python.instructions.md:10-12); rest on-demand via INDEX | 79,422 | 19,856 | GS tooling refs. python-tsdb + python-chunk are Brazil-desk examples (eq1d_brazil, PETR4.SA, Sao_Paulo tz) yet auto-recommended for every .py edit in a US-equity project. Both exce |
| `workflows/fix.md` | workflow | on-demand ('fix it.prompt.md' shim, keyword) | 16,228 | 4,057 | Largest workflow: 8-state pipeline, dual paths, checkpoint contracts. Constraints (lines 270-273) still name deleted personas QUARTERMASTER/PRESCRIBER/AUDITOR. Line 277 lint-gate r |
| `workflows/learn.md` | workflow | on-demand (learn.prompt.md shim, keyword, yields from research/debug/cure) | 11,925 | 2,981 | 2nd-largest. Dual-kind (memory/fix) distillation with mandatory user approval. Well-specified composition interface; caps at 5 candidates/kind. |
| `workflows/research.md` | workflow | on-demand (research.prompt.md shim, keyword) | 8,280 | 2,070 | ORIENT/FOCUS/EXPLORE/DOCUMENT session. Its session protocol is duplicated in condensed form inside research.prompt.md — two copies to drift. Duplicate numbered '4.' in ORIENT actio |
| `workflows/team.md` | workflow | on-demand (team.prompt.md shim; escalation from plan/execute at 3+ streams) | 7,900 | 1,975 | Leader/worker orchestration, max 6 workers. Line 217 forbids worker sub-spawning — contradicts depth-2 allowance in subagent_protocol.md:65 and AGENTS.md:25. Line 104 invokes VS Co |
| `workflows/plan.md` | workflow | on-demand (plan.prompt.md shim, keyword, default route) | 7,787 | 1,947 | Default workflow. DESIGN phase embeds a 3rd copy of the context-packet YAML schema (lines 78-88). Forbids plan→execute→plan at line 159 — contradicted by execute.md:76. |
| `workflows/lightweight.md` | workflow | on-demand (lightweight.prompt.md shim, keyword) | 7,075 | 1,769 | Budget mode; BUDGETEER only. 7KB is heavy for a workflow whose purpose is minimal context — the mode's own spec costs ~1.8k tokens. |
| `workflows/refactor.md` | workflow | on-demand (refactor.prompt.md shim, keyword) | 6,196 | 1,549 | SCOPE/LOCK/RESTRUCTURE/VERIFY; test-lock-first. Skimmed — no anomalies in scanned portion. |
| `workflows/execute.md` | workflow | on-demand (execute.prompt.md shim, keyword, plan.md yield) | 4,459 | 1,115 | Subagent orchestration via `runSubagent` tool (line 34). IMPLEMENT phase (TEST-FIRST/CONFORM/scope-drift) near-verbatim duplicate of fix.md IMPLEMENT. Line 76 allows yield back to |
| `workflows/interview.md` | workflow | on-demand (keyword/yield only — NO prompt shim exists) | 4,105 | 1,026 | Clarification workflow. Reachable only via keyword routing (shared ambiguously with plan.md) and yields from plan/fix/learn. No interview.prompt.md. |
| `workflows/debug.md` | workflow | on-demand (debug.prompt.md shim, keyword) | 3,328 | 832 | DIAGNOSE/FIX/VERIFY, max 2 loops. Unlike fix.md, its FIX state writes code despite TRACEHOUND being no-fix — persona applies to DIAGNOSE only. Skimmed. |
| `workflows/cure.md` | workflow | on-demand (cure.prompt.md shim, keyword, fix.md yield) | 3,266 | 817 | Design-compliance remediation; loads the four */design.md specs. Has pragmatism filter to skip ceremony-only fixes. |
| `workflows/review.md` | workflow | on-demand (review.prompt.md shim, keyword) | 2,785 | 696 | EVAL-SENTINEL checklist review; severity table + verdict. Skimmed, coherent. |
| `workflows/bootup.md` | workflow | on-demand (bootup.prompt.md shim only, per INDEX.md:37) | 2,088 | 522 | Session-start checklist duplicating AGENTS.md Boot Protocol (same 4 reads + handoff check) — two copies of boot sequence. |
| `workflows/housekeep.md` | workflow | on-demand (lint-workspace.prompt.md shim, keyword) | 2,034 | 509 | Thin SCAN/FIX/VERIFY loop. Entry says 'User explicitly uses /lint-workspace or /housekeep' but no housekeep.prompt.md exists — /housekeep is a phantom command. |
| `workflows/progress.md` | workflow | on-demand (progress.prompt.md shim, keyword) | 1,395 | 349 | Weekly-log synthesis with strict format rules (no em dashes, plain language). Duplicates format spec also in AGENTS.md:86. |
| `workflows/INDEX.md` | workflow-registry/router | on-demand (AGENTS.md:7 routing rule directs here when no /prompt) | 3,685 | 921 | 15-workflow registry + keyword dispatch + skill dispatch. Keywords 'don't assume'/'let's discuss' appear in BOTH Plan (line 23) and Interview (line 36) rows — ambiguous dispatch. |

*Phase 1–2 · Findings*

## 84 findings, most-severe first

Each finding was raised by a dimension auditor, merged to remove duplicates, then attacked by adversarial verifiers (2 refuters for `BLOCKER`/`HIGH`, 1 for others) whose default stance was “this is wrong.” None were refuted; 55 were adjusted (evidence/severity corrected) and re-confirmed; 28 confirmed outright; 1 contested. IDs prefixed `AW-G` come from the completeness-critic's gap-chase round.

## Severity: Blocker (6 findings) — broken · silent-failure · security

### AW-01 — Two live GS Confluence Personal Access Tokens committed in the tracked tree

**BLOCKER · security · effort: small · CONFIRMED**

**Location:** `workspace/config/.env:1` · `memory/_dormant/ref/gssso-auth.md:87` · `skills/CONFLUENCE/SKILL.md:50` · `skills/CONFLUENCE/src/client.py:104`

**Evidence:** .env:1 `CONFLUENCE_PAT=[REDACTED-PAT]`; gssso-auth.md:87 `$pat="[REDACTED-PAT]"`. Two DISTINCT Atlassian PATs (`<numericId>:<secret>` base64), confluence.work.gs.com committed alongside; .env is git-tracked and NOT gitignored.

**Why it matters:** Usable bearer credentials for GS internal Confluence REST API on a snapshot now on a personal Windows machine. Anyone with the repo can read/write Confluence as the token owner. CONFLUENCE/SKILL.md:50 institutionalizes it by telling agents to keep the secret in a tracked path.

**Recommended fix:** Revoke BOTH tokens at confluence.work.gs.com usertokens page. `git rm --cached workspace/config/.env`, add `/workspace/config/.env` + `*.env` to .gitignore, ship .env.template, replace gssso-auth.md:87 literal with `$env:CONFLUENCE_PAT`, purge history.

### AW-02 — Entire internal-GS tooling snapshot (credentials, endpoints, PII) resides on a personal off-perimeter machine

**BLOCKER · security · effort: large · ADJUSTED-CONFIRMED**

**Location:** `workspace/config/.env:1` · `skills/NDS_INFRA/SKILL.md:76` · `memory/_dormant/ref/gssso-auth.md:87`

**Evidence:** Tracked tree contains 34 unique https://*.gs.com endpoints (54 hostname mentions incl. placeholders), 2 distinct hardcoded Confluence PAT literals (workspace/config/.env:1 "CONFLUENCE_PAT=[REDACTED-PAT]"; memory/_dormant/ref/gssso-auth.md:87 "$pat = \"[REDACTED-PAT]\""), and employee PII in skills/NDS_INFRA/SKILL.md:76/91/93 (jane.doe@example.gs.com, Serial:{serial}, lastIP 10.0.0.1). .gitignore has no .env entry, so the secret file is git-tracked. Liveness of the PATs is unverifiable from this machine (HYPOTHESIS; confluence-auth.md:65 notes expiry) but committed tokens must be treated as compromised. Ironically the repo's own guidance forbids this: confluence-auth.md:78 "Hardcoding Bearer <token> ... leaks in logs".

**Why it matters:** Aggregate is a reportable data-exfiltration/insider-risk event: internal SDLC tooling, network topology, auth mechanisms and live tokens have crossed the corporate boundary onto an unmanaged endpoint.

**Recommended fix:** Treat as a security incident: revoke/rotate both PATs, report exposure per firm policy, and purge internal-only material from off-firm copies. Mechanically: add workspace/config/.env to .gitignore and `git rm --cached` it (skills/CONFLUENCE/SKILL.md:50 already expects the PAT via that local env file, so untracking breaks nothing); redact real employee PII in skills/NDS_INFRA/SKILL.md example tables to synthetic values; replace the literal token at memory/_dormant/ref/gssso-auth.md:87 with an env-var read, matching the repo's own rule at confluence-auth.md:78.

### AW-03 — commandAllowlist terminal:["*"] auto-approves every terminal command; additionalReadAccessPaths grants the whole H: drive

**BLOCKER · security · effort: small · ADJUSTED-CONFIRMED**

**Location:** `ml-vol-estimator.code-workspace:24` · `ml-vol-estimator.code-workspace:21`

**Evidence:** ml-vol-estimator.code-workspace:21-23 `"github.copilot.chat.additionalReadAccessPaths": ["h:/"]`; :24-26 `"github.copilot.chat.commandAllowlist": {"terminal": ["*"]}`. Sole occurrences in tracked tree (grep -c = 1 each). Neither key exists in the official Copilot settings reference (real: `chat.tools.terminal.autoApprove` command->bool map; `github.copilot.chat.additionalReadAccessFolders` array) — stock VS Code silently ignores unknown keys, so the Allow gate may remain intact on stock builds. HYPOTHESIS: the GS-internal VS Code build (workspace uses custom `slang:/` folder URIs, :4-13) honors these names; confirm by checking the internal Copilot extension's package.json settings contributions. Either way the committed artifact encodes auto-approve-everything + whole-H:-drive read intent in a shared repo file.

**Why it matters:** The wildcard removes the human 'Allow' gate for ALL shell commands Copilot proposes — the primary control against a runaway/prompt-injected agent — and h:/ exposes the entire drive (venvs, all-languages-env.cmd, secrets). Defeats the workflow's own Zero-Allow intent; a single injected instruction becomes read-broadly + arbitrary-exec.

**Recommended fix:** Delete both keys from ml-vol-estimator.code-workspace:21-26. If terminal auto-approval is wanted, use the real setting `chat.tools.terminal.autoApprove` with an explicit command->true map (./vol, git status, workspace/lint/lint_task.*) — never a wildcard — and prefer user-level over the committed workspace file. Scope external read access via the real `github.copilot.chat.additionalReadAccessFolders` to the exact H: venv subpath, not "h:/". If these names are GS-fork-specific, apply the same narrowing to the fork's keys.

### AW-04 — Task args-file interface has divergent specs: SKILL.md/prompt {run_id} filenames vs fixed paths the tasks read — commit/lint silently replay stale or wrong-suite args

**BLOCKER · broken · effort: medium · ADJUSTED-CONFIRMED**

**Location:** `skills/GIT/SKILL.md:29` · `skills/GIT_COMMIT/SKILL.md:37` · `skills/SLANG_TEST_COVERAGE/SKILL.md:33` · `skills/SLANG_LINT/SKILL.md:119` · `.github/prompts/slang-review.prompt.md:29` · `.github/prompts/lint-workspace.prompt.md:16` · `ml-vol-estimator.code-workspace:94` · `ml-vol-estimator.code-workspace:198` · `ml-vol-estimator.code-workspace:68` · `ml-vol-estimator.code-workspace:59`

**Evidence:** Corrections: (1) Absent args file is NOT silent — _run.cmd:45-48 "if not exist %_AF% ... exit /b 1" and _run.sh:66-67 fail fast with exit 1. The silent path is: stale fixed args file present → _run.cmd:50 deletes old out_file, replays stale args (e.g. old git push in git_args.json), then _run.cmd:57-59 "Always exit 0" masks any Python failure; workspace/tmp is not gitignored (.gitignore:31 covers only .pytest_cache/), so stale args persist across sessions. (2) SLANG_LINT SKILL.md:119 is internally consistent — lines 122-129 mandate create_and_run_task passing the {run_id} args file explicitly, so that skill alone works; its breakage is the contradiction with slang-review.prompt.md:29-31 (writes lint_args.json, launches lint-slang which reads slang_lint_args.json per ws:68, polls slang_lint_results.json) and lint-workspace.prompt.md:56 ("Never use create_and_run_task"), which forbids the only mechanism that makes {run_id} filenames work. All other cited quotes verified verbatim: GIT/SKILL.md:29 git_args_{run_id}.json vs ws:94 git_args.json; GIT_COMMIT/SKILL.md:37 git_commit_args_{run_id}.json vs ws:102 git_commit_args.json; SLANG_TEST_COVERAGE/SKILL.md:33 epssp_coverage_args.json + :41 run_task(id="slang-test-coverage") vs ws:198 slang_test_coverage_args.json; lint-workspace.prompt.md:16 lint_args_{run_id}.json vs ws:59 lint_args.json.

**Why it matters:** run_task can't override args, so following the docs makes it read an absent file (task errors but _run exits 0 → agent polls a {run_id} out_file that never appears) or a STALE file from a prior session — silently re-running an old commit/push or linting the wrong scripts; slang-review's fabricated 'Lint pass' auto-fill is built on it. No lint cross-checks SKILL.md filenames against task defs.

**Recommended fix:** Fix stands with two additions. Making fixed workspace/tmp/<name>_args.json the single contract and keeping run_id as a JSON field is safe: lint.py:498 reads run_id from the args body and lint.py:514-517 still derives slang_lint_results_{run_id}.json, preserving concurrent-session-unique results. But (a) also update SLANG_LINT/SKILL.md:107-131, which currently mandates create_and_run_task with {run_id} args filenames — otherwise it contradicts both the new contract and lint-workspace.prompt.md:56; (b) in slang-review.prompt.md, fix line 29 to slang_lint_args.json AND line 31's poll target, which must match lint.py's derived slang_lint_results_{run_id}.json when a run_id is supplied (or omit run_id there); (c) the proposed lint check belongs in the workspace/lint suite that lint-workspace.prompt.md:45 already advertises as "vscode tasks — tasks.json validity", cross-checking each task's --args-file against the filename strings in its SKILL.md/prompt. Note the args-file fixed names reintroduce last-writer-wins contention between concurrent agents on the args file itself (only results files stay unique) — acceptable, but state it in the SKILL.mds since GIT/SKILL.md:29 currently promises collision avoidance.

### AW-05 — MODEL_TRAIN / NOTEBOOK / RESEARCH task wrappers invoke nonexistent Python modules — core skills dead end-to-end

**BLOCKER · broken · effort: small · ADJUSTED-CONFIRMED**

**Location:** `skills/MODEL_TRAIN/src/train_task.cmd:43` · `skills/NOTEBOOK/src/notebook_task.cmd:41` · `skills/RESEARCH/src/research_task.cmd:40` · `src/volforecast/cli/research.py:44` · `skills/NOTEBOOK/SKILL.md:135` · `skills/EVALUATE/src/eval_task.cmd:44`

**Evidence:** All confirmed, plus: eval_task.cmd:42 (not 44) `python -m volforecast.evaluation.evaluate` — module absent (evaluation/ has metrics.py etc., no evaluate.py). feature_task.cmd:42 `-m volforecast.features.build` — absent. The .sh twins are NOT working alternatives: train_task.sh:56, notebook_task.sh:56, research_task.sh:56, eval_task.sh:56 invoke the same nonexistent modules (they differ only in having the stale-output-delete block, e.g. train_task.sh:46-53, and `exit 0` at :64, which _run.cmd:50,59 has but the bespoke .cmd wrappers lack). cli/notebook.py:35 main() also raises NotImplementedError, so both cli stubs (notebook.py, research.py) are dead, and both want --config (notebook.py:20) while wrappers pass --args-file. AGENTS.md:183/186/187 lists MODEL_TRAIN/RESEARCH/NOTEBOOK in the project-relevant skills table; AGENTS.md:157 "NEVER fall back to run_in_terminal... HARD RULE". NOTEBOOK/SKILL.md:151 steers agents to run_task("notebook"). No tracked .vscode/tasks.json defines these tasks (only .vscode/settings.json is tracked) — so on a fresh checkout run_task fails before the wrapper; in the original workspace the wrapper's ModuleNotFoundError is the failure mode.

**Why it matters:** MODEL_TRAIN/NOTEBOOK are named in always-on AGENTS.md core-skills; agents are steered into ModuleNotFoundError. Failure is silent: .cmd wrappers (unlike .sh twins) lack stale-output deletion (EVALUATE/FEATURE_BUILD too), and success is signaled only by out_file existence, so a leftover result from a prior run reads as fresh. AGENTS.md:157 forbids the run_in_terminal fallback.

**Recommended fix:** Fix must cover BOTH .cmd and .sh wrappers (all four skills: MODEL_TRAIN, NOTEBOOK, RESEARCH, EVALUATE, plus FEATURE_BUILD's features.build). Re-pointing NOTEBOOK/RESEARCH at volforecast.cli.notebook/.research is insufficient — both cli stubs raise NotImplementedError (notebook.py:35, research.py:44) and take --config not --args-file; implement them or delete the task paths and mark the skills agent-driven-only. For MODEL_TRAIN/EVALUATE, route through the working experiment path (`./vol run` → `python -m volforecast run`; cli/experiment.py has 0 NotImplementedError). Port the stale-output-delete + exit-0 block from _shared/_run.cmd:44-59 into the bespoke .cmd wrappers (or convert them to 3-line _run.cmd callers as _run.cmd:8-11 documents). Fix NOTEBOOK/SKILL.md:135-136 imports to volforecast.features/evaluation.

### AW-06 — CI has never run and cannot pass: push trigger misses the default branch and deps require the GS-internal PyPI mirror

**BLOCKER · broken · effort: small · ADJUSTED-CONFIRMED**

**Location:** `.github/workflows/ci.yml:5` · `.github/workflows/ci.yml:28` · `src/uv.toml:7`

**Evidence:** ci.yml:5 `branches: [main, develop]` correctly names the default branch (`gh api repos/xRyann2255/ML-GS --jq .default_branch` → `main`; local `origin/HEAD -> origin/master` is stale). But `git ls-tree origin/main` shows no `.github/` dir — ci.yml exists only on presentation/refactor branches, and push events run the workflow file on the pushed ref, so pushes to main run nothing and pushes to presentation/refactor don't match `[main, develop]`. `gh api .../actions/runs --jq .total_count` → 0; workflows API empty. Any PR run (ci.yml:6-7 `branches: ["**"]`) would still die at ci.yml:28 `uv sync --dev`: working-directory `src` (ci.yml:14) makes uv read src/uv.toml:7/:10-11 whose sole default index is `https://pypi.aws.site.gs.com/repository/pypi-group/simple/`, unreachable from ubuntu-latest. /debug hint is at ci.yml:45, not 44.

**Why it matters:** The only automated quality gate is dead config: master pushes never trigger it, and any PR run fails at dependency install on a public ubuntu runner before ruff/mypy/pytest. Every downstream quality claim (TDD gate, lint gate) has no backstop; the ci.yml:44 /debug hint fires on infra failure, not test failure.

**Recommended fix:** Land .github/workflows/ci.yml on the default branch `main` (merge presentation, or add the active branches to the push trigger) — do NOT change to `branches: [master, main]`; master is not the GitHub default and lacks the file too. Separately, make deps installable on public runners: set `UV_INDEX_URL=https://pypi.org/simple` (or a CI-only uv config) in the workflow env, or explicitly document/disable ci.yml as GS-internal-runner-only.

## Severity: High (20 findings) — broad context waste or quality defect

### AW-G2 — 'Non-negotiable' Opus-4.6 subagent mandate is structurally unenforceable — no fallback model is named and VS Code provides no hard enforcement

**HIGH · broken · effort: small · CONFIRMED**

**Location:** `.github/copilot-instructions.md:72` · `AGENTS.md:23` · `policy/subagent_protocol.md:14` · `workflows/execute.md:35` · `workflows/execute.md:106` · `workflows/refactor.md:88` · `workflows/research.md:88`

**Evidence:** copilot-instructions.md:72 "All subagents MUST use Claude Opus 4.6... This is non-negotiable". AGENTS.md:23 "All subagents MUST use Claude Opus 4.6. No exceptions." subagent_protocol.md:14 "If the environment offers model selection, always choose Opus 4.6." VS Code has no mechanism to hard-fail a prompt whose model is unavailable.

**Why it matters:** The mandate is textual guidance to a model/human, not an enforced constraint. If the selector lacks 'Opus 4.6' the instruction is inoperative and NO alternate model is designated anywhere, so behavior is undefined — the agent proceeds on whatever is selected. 7 always-on/workflow lines assert a guarantee the platform cannot uphold.

**Recommended fix:** Replace the absolute mandate with a graceful policy: name a verified primary AND an explicit fallback (e.g. 'prefer <verified-id>; if unavailable use the current flagship and note it'). subagent_protocol.md:14 already has a degradation clause — propagate that pattern to copilot-instructions.md:72 and AGENTS.md:23 instead of 'No exceptions'.

### AW-G3 — Model pinned as a hardcoded display-name literal in 76 places — fragile against documented Copilot catalog churn; a version bump is a 34-file edit

**HIGH · architecture · effort: medium · CONFIRMED**

**Location:** `.github/prompts/ (34 frontmatter sites)` · `.github/copilot-instructions.md:72` · `AGENTS.md:23` · `policy/subagent_protocol.md:14` · `workflows/execute.md:35`

**Evidence:** `grep -ri 'opus 4.6|opus-4-6'` across tracked root → 76 mentions (34 prompt frontmatter + 42 prose). GitHub changelog 2026-05-20 removed models from Copilot; Sonnet 5 went GA Jun 30 2026 — VS Code docs: 'The list of available models might vary and change over time.'

**Why it matters:** Copilot's model roster demonstrably rotates, so any pinned literal has a short shelf life. There is no single source of truth / variable indirection — every prompt hardcodes the string in YAML frontmatter, so re-pinning to the next model requires editing all 34 prompt files plus prose, inviting partial drift where some prompts lag.

**Recommended fix:** Centralize the intended model in one referenced location (e.g. a single line in AGENTS.md / subagent_protocol.md that all prompts defer to) and have prompts omit `model:` (inherit picker) rather than each restating the literal. If per-prompt pinning is required, script the bulk update so all 34 stay in lockstep.

### AW-07 — Two mutually exclusive execution architectures both mandated as universal HARD rules; ./vol is Linux-only while the skill layer is Windows/H:-only

**HIGH · broken · effort: medium · ADJUSTED-CONFIRMED**

**Location:** `.github/copilot-instructions.md:15` · `.github/copilot-instructions.md:30` · `AGENTS.md:157` · `vol:60` · `vol:342` · `skills/SLANG_REVIEW/SKILL.md:44` · `.github/prompts/slang-review.prompt.md:52` · `.github/prompts/glimpse.prompt.md:13` · `.github/instructions/python.instructions.md:30`

**Evidence:** Always-on conflict confirmed: copilot-instructions.md:3/:15/:30 unconditional ("ALL agents in ALL modes"; "NEVER run python/pytest/pip/uv/mypy"; "Run ALL commands via ./vol exec/bg"); AGENTS.md:157 run_task-only "zero exceptions"; vol:1 bash, :60 source .venv/bin/activate, :342 setsid — no OS guard, dead on Windows. Prompts/skills mandate violating PowerShell: slang-review.prompt.md:52 + SLANG_REVIEW/SKILL.md:44 "PYTHON skills/SLANG_REVIEW/src/review.py", glimpse.prompt.md:13; PYTHON_PATH/SKILL.md:38 falls back to H:\venv311\Scripts\python.exe; python.instructions.md:30 Windows branch uses `uv run python` directly, contradicting rule 2. CORRECTION: the skill task layer is NOT Windows-only — all ~40 skills ship paired .sh/.cmd wrappers (skills/_shared/_run.sh Linux bootstrap with python3 fallback), and ml-vol-estimator.code-workspace tasks have per-OS commands ("command": "...task.sh", "windows": {"command": "...task.cmd"}). Windows hardcoding sits inside secexpr-class skill Python (review.py:54 ENV_CMD=r"H:\all-languages-env.cmd") only. Tasks tracked only in code-workspace:51+; no .vscode/tasks.json (git ls-files: only .vscode/settings.json) — absent for folder-open and coding agent, which also lacks run_task entirely vs AGENTS.md:157.

**Why it matters:** On Windows every ./vol call dies (no setsid/.venv/bin) yet the HARD rule forbids the only fallback; on Linux/coding-agent every run_task skill dies on H:\ paths. No OS conditional exists in either always-on file, so the break is silent — the agent hits dead ends or must violate a 'zero-exception' rule to run any skill, eroding compliance everywhere. run_task tasks also exist only in the .code-workspace, absent when the folder is opened directly or by the coding agent.

**Recommended fix:** Scope copilot-instructions.md rules 2/3/8 and AGENTS.md:157 explicitly: ./vol mandate applies to src/ Python on the Linux/Coder workspace; GS Windows skills execute via run_task per SKILL.md (the per-OS .sh/.cmd wrapper pairs already exist — the rule text just needs to acknowledge them); carve a run_in_terminal exception for environments without run_task (Copilot coding agent). Add an OS guard to vol (fail loudly with a pointer on non-Linux). Move task definitions from ml-vol-estimator.code-workspace:51+ into a tracked .vscode/tasks.json so folder-open sessions get them. Fix .github/prompts/gsvivs-audit.prompt.md:141 ("Use `python3` for parsing") which contradicts :146's ./vol mandate — line 141, not 142. Align python.instructions.md:30 Windows branch with rule 2 or scope rule 2 to Linux.

### AW-08 — Live API credentials transmitted over TLS with certificate verification disabled (CERT_NONE) across six clients

**HIGH · security · effort: medium · ADJUSTED-CONFIRMED**

**Location:** `skills/_shared/gitlab_auth.py:48` · `skills/PRIME_QUERY/src/prime.py:82` · `skills/DIRGET/src/dirget.py:78` · `skills/CONFLUENCE/src/client.py:62` · `skills/TMD/src/tmd.py:40` · `skills/FORWARD_NETWORK/src/fwd_api.py:97`

**Evidence:** gitlab_auth.py:48-49 CERT_NONE ctx used at :63 with PRIVATE-TOKEN (:43); mr_task.py:89-90 POST /merge_requests over it proves MR-write PAT exposure. prime.py:82-83 + GSSSO :86; dirget.py:78-79 AND second block :100-102 + GSSSO :105; client.py:62 verify_ssl=False, Bearer :75, session.verify :80, from_env defaults "false" :120; tmd.py:40 verify=False AND CERT_NONE :75-77 + GSSSO :81; fwd_api.py:91 ssl._create_unverified_context() with Basic auth :84-86. Correct pattern exists at etask.py:137 and :519.

**Why it matters:** Each sends a bearer secret (GitLab PAT with MR-write, GSSSO firm-wide cookie, Confluence PAT) over a channel where cert+hostname are unvalidated; any on-path attacker can MITM and capture it. The write-capable GitLab PAT is the worst.

**Recommended fix:** Replace CERT_NONE/unverified contexts with ssl.create_default_context() (works on internal GS hosts per etask.py:137, since Windows Python loads the machine cert store incl. corporate roots); where a custom CA is needed, load C:\ProgramData\certificates\cacerts.cer via cafile, matching symphony.py:25-27 REQUESTS_CA_BUNDLE. Flip CONFLUENCE verify_ssl default to True in BOTH __init__ (client.py:62) and the from_env env-var default (client.py:120). Also fix the second dirget.py block (:100-102) and tmd.py's own CERT_NONE block (:75-77), which the finding's location list omits.

### AW-09 — 'Zero Allow' create_and_run_task pattern is a deliberate permission-gate bypass, and lint.prompt.md forbids the very thing the skill mandates (tool choice + polling)

**HIGH · security · effort: small · ADJUSTED-CONFIRMED**

**Location:** `skills/SLANG_LINT/SKILL.md:99` · `skills/SLANG_LINT/SKILL.md:136` · `.github/prompts/lint.prompt.md:13` · `.github/prompts/lint.prompt.md:31` · `skills/SLANG_REVIEW/SKILL.md:163` · `skills/SLANG_REVIEW/SKILL.md:241`

**Evidence:** All original quotes confirmed at cited lines. Additional corroboration: SLANG_LINT is internally inconsistent too — :99/:122 say create_and_run_task but its own table :157 says 'Launch task | run_task'; SLANG_REVIEW:117 says run_task("slang-review") while :149 says create_and_run_task. Root cause is documented policy: memory/ref/vscode-tasks.md:96 rule E3 'Use create_and_run_task when run_task can't find predefined tasks | Fallback for multi-workspace .code-workspace task definitions'. Repo-wide, ~25 other skills standardize on run_task with predefined labels (e.g. GIT:58, SLANG_GLIMPSE:126), making SLANG_LINT/SLANG_REVIEW the outliers. HYPOTHESIS (unverifiable from tree): whether create_and_run_task truly skips the Allow prompt in current VS Code — .vscode/settings.json:1-8 has no chat.tools.autoApprove or task auto-approval config; the 'no Allow' claim rests solely on the skill text. The bypass INTENT is explicit in-file either way, and the tool accepts arbitrary type:shell commands, so the training-the-model concern stands. Note the example task's command is a fixed .cmd path; only label/args interpolate agent-composed {run_id}, so injection surface in the documented pattern is via run_id reaching shell args, not a free-form command — but nothing constrains the model to that template once told create_and_run_task is the no-prompt path.

**Why it matters:** create_and_run_task with type:shell executes ANY command with no user approval — training the model to route around the permission system, so prompt-injected commands inherit zero-prompt exec. Simultaneously the prompt (which orders 'read the skill FIRST') and the skill give mutually exclusive tool/polling instructions, and Start-Sleep polling requires the run_in_terminal both ban.

**Recommended fix:** Standardize on run_task with predefined labels: in skills/SLANG_LINT/SKILL.md replace :99/:122 create_and_run_task instructions with run_task("lint-slang") (label already referenced by lint.prompt.md:13 and memory/slang/lint-edit.md:20, and SKILL:157's own table already says run_task); in skills/SLANG_REVIEW/SKILL.md fix :149/:163 to run_task("slang-review") matching :117, and delete/reword :241 and :247 60s-polling notes (run_task blocks per vscode-tasks.md E7). Delete lint.prompt.md:31 Start-Sleep polling rule (impossible under its own :13 terminal ban). CRITICAL addition the original fix missed: also amend memory/ref/vscode-tasks.md:96 rule E3, which still endorses create_and_run_task as a fallback — leaving it makes memory contradict the fixed skills; replace with 'if run_task can't find the task, stop and ask the user' or fix workspaceFolder-based task discovery. Constrain run_id to [a-z0-9-] in both skills' args-file docs.

### AW-G9 — No copilot-setup-steps.yml: ./vol hard-exits on the coding agent's runner (no uv, no nix), and every fallback is forbidden — the entire compute path is dead

**HIGH · broken · effort: large · ADJUSTED-CONFIRMED**

**Location:** `vol:20` · `vol:49` · `AGENTS.md:215` · `AGENTS.md:217` · `.github/copilot-instructions.md:15` · `.github/workflows/ci.yml:1`

**Evidence:** Verified: `git ls-files .github/workflows/` returns only `ci.yml` — no `copilot-setup-steps.yml`. vol:20 `if ! command -v uv &>/dev/null;` -> vol:21 exits with `Install via: nix-env -iA nixpkgs.uv`; vol:44 `nix-store --query`; vol:51 `uv sync --frozen`. AGENTS.md:216 "Tools are on PATH via nix. No env scripts needed." copilot-instructions.md:30 "Run ALL commands via ./vol exec or ./vol bg." SCOPE CORRECTION: the hard-exit only bites on GitHub's stock Ubuntu coding-agent runner (no nix/uv). The primary consumer, VS Code Copilot Chat, runs inside the nix-provisioned Coder workspace declared at AGENTS.md:212 where uv/nix are present, so vol is fully reachable there. ci.yml's `astral-sh/setup-uv@v3` (line 25) provisions uv only for the CI job, not the agent session.

**Why it matters:** GitHub Docs: the coding agent runs in an ephemeral Ubuntu x64 runner and copilot-setup-steps.yml is the documented way to 'Preinstall tools or dependencies'. A stock runner has neither uv nor nix (nor nix-env to install uv). So `./vol` fails at line 20 on every invocation. Yet AGENTS.md:217 and copilot-instructions.md:15 say NEVER run python/pytest/uv/mypy directly and copilot-instructions.md:30 says run ALL commands via `./vol exec`. The agent is ordered to use the one tool that cannot start and forbidden from the raw tools it actually has — a hard deadlock. 0% of ./vol is reachable.

**Recommended fix:** Add `.github/workflows/copilot-setup-steps.yml` with a job named `copilot-setup-steps` that installs Python 3.11 + uv (astral-sh/setup-uv) and runs `uv sync`, so the coding-agent runner can start vol. Additionally gate vol's nix assumptions (vol:38-45 nix-store probe; vol:21 nix-env hint) behind an "is nix present" check so a non-nix runner degrades gracefully instead of hard-exiting. Severity is HIGH not BLOCKER because the confirmed VS Code Chat consumer is unaffected; this only blocks the optional coding-agent path.

### AW-10 — CONFLUENCE skill mandates storing the PAT in git-tracked workspace/config/.env (not gitignored) and defaults TLS verification off

**HIGH · security · effort: small · ADJUSTED-CONFIRMED**

**Location:** `skills/CONFLUENCE/SKILL.md:50` · `skills/CONFLUENCE/SKILL.md:189` · `skills/CONFLUENCE/src/client.py:120` · `.gitignore:28`

**Evidence:** skills/CONFLUENCE/SKILL.md:50 "CONFLUENCE_PAT set in workspace/config/.env" (verbatim). SKILL.md:189 "Keep verify_ssl=False (default) — GS internal certs use custom CA" (verbatim). client.py:104 resolves dotenv_path to workspace/config/.env; client.py:120 `verify = os.environ.get("CONFLUENCE_VERIFY_SSL", "false").lower() == "true"`; client.py:62 `verify_ssl: bool = False`. .gitignore:9 ignores only /workspace/config/user.json — no .env pattern anywhere (git check-ignore workspace/config/.env exits 1). STRONGER THAN CLAIMED: workspace/config/.env is tracked at HEAD (`git ls-files` lists it) and contains a live 44-char CONFLUENCE_PAT plus CONFLUENCE_URL=https://confluence.work.gs.com/. Path also documented in memory/_dormant/ref/confluence-auth.md:24,66.

**Why it matters:** The documented credential-storage location is inside the tracked tree and unignored, so following the skill writes a secret into version control — exactly what happened (AW-01). The verify-off advice guarantees the PAT is also sent over an unauthenticated channel.

**Recommended fix:** 1) Revoke/rotate the leaked PAT (it is in HEAD, not just at risk). 2) git rm --cached workspace/config/.env; add `/workspace/config/.env` (and optionally `*.env`) to .gitignore next to line 9. 3) Ship workspace/config/.env.template (keys only) mirroring existing user.json.template in that dir. 4) Update SKILL.md:50 to state .env is gitignored/never committed, and memory/_dormant/ref/confluence-auth.md:24,66 which document the same path. 5) Flip default: client.py:62 verify_ssl=True, client.py:120 default "true", and point requests at the GS CA bundle (CONFLUENCE_CA_BUNDLE env var passed to session.verify); rewrite SKILL.md:189 troubleshooting row to say install the GS CA bundle instead of keeping verify off. Fix is safe: only client.py from_env() and the two doc files reference the path, and gitignoring does not remove the on-disk file the client reads.

### AW-11 — Prompt context files are bare backtick paths (0 of 34 use Markdown links); AGENTS.md falsely claims skill/persona/workflow content is auto-injected

**HIGH · broken · effort: small · ADJUSTED-CONFIRMED**

**Location:** `AGENTS.md:62` · `.github/prompts/bootup.prompt.md:6` · `.github/prompts/learn.prompt.md:6` · `.github/prompts/lightweight.prompt.md:6` · `.github/prompts/slop-cleaner.prompt.md:7` · `.github/prompts/backtest.prompt.md:9` · `.github/prompts/plan.prompt.md:11`

**Evidence:** AGENTS.md:62 'the full skill guide, persona instructions, and related knowledge are injected automatically.' grep '](' across all 34 .github/prompts/*.prompt.md = 0 files. bootup.prompt.md body is exactly '- `workflows/bootup.md`'. Gated layer measured: workflows/*.md 99,892 B + personas/*.md 19,473 B (~30k tok). implementation_boundary.md:72 states the intended contract ('agent reads backtick-referenced files on demand via read_file') but only in an on-demand policy file; no always-on file states it.

**Why it matters:** VS Code attaches nothing for backtick code-spans, so the ~35KB second-hop layer (workflows, 5 personas, skill guides) loads only if the model volunteers read_file — and the always-on file tells it loading already happened, actively discouraging the read. /bootup, /learn, /lightweight, /slop-cleaner deliver a verbless one-line body plus a wrong belief; a slash command can resolve to near-empty context.

**Recommended fix:** Do NOT convert bullets to Markdown links — that is deliberately banned (implementation_boundary.md:64-70, VS Code prompts-diagnostics false positives) and lint-enforced by workspace/lint/lint_vscode_md.py:238 file-ref-in-prompt and :274 prompt-link-in-prompt. Instead: (1) prefix each verbless prompt body with 'Read each file below with read_file before acting'; (2) rewrite AGENTS.md:62 to 'the prompt lists backtick-referenced files the agent must read via read_file — read them before acting.'

### AW-12 — ~13-51 skill→memory references broke after a half-finished _dormant migration; invisible to lint_broken_refs.py

**HIGH · broken · effort: small · ADJUSTED-CONFIRMED**

**Location:** `skills/SLANG_EDIT/SKILL.md:247` · `skills/SECDB_POSITION/SKILL.md:29` · `skills/ETASK/SKILL.md:48` · `skills/OUTLOOK/SKILL.md:222` · `skills/CANVAS/SKILL.md:258` · `skills/FORWARD_NETWORK/SKILL.md:61` · `skills/RESEARCH/SKILL.md:50` · `workspace/lint/lint_broken_refs.py:80`

**Evidence:** 51 broken memory/ refs across 27 (not 24) SKILL.md files; 48 have counterparts in memory/_dormant/ (ref 28, sys 4, slang 16), 3 truly gone: RESEARCH:50 and RESEARCH:145 (both memory/research/open-questions.md; real file at workspace/research/open-questions.md) and SEARCH:75 memory/sys/gs-trade-flows.md (untracked, absent everywhere). 50 of 51 are bare plain-text paths, 1 backtick (RESEARCH:50, suppressed by table-header 'Content' indicator). Running lint_broken_refs.py reports only 2 broken refs, zero in skills/ — its _MD_LINK/_BACKTICK_REF/_FILE_DIRECTIVE regexes never match plain-text bullets and _dormant is in SKIP_DIRS.

**Why it matters:** These Links are the skills' progressive-disclosure layer; an agent following them gets file-not-found on every one (e.g. GSSSO auth for CANVAS 401 recovery, secexpr gotchas for OUTLOOK) and proceeds without the safety knowledge. The linter can't catch it, so the rot is permanent-by-default.

**Recommended fix:** Batch-rewrite memory/(ref|sys|slang)/X.md -> memory/_dormant/\1/X.md for the 48 moved targets; repoint both RESEARCH refs (:50, :145) to workspace/research/open-questions.md; separately fix SEARCH:75 memory/sys/gs-trade-flows.md which the (ref|sys|slang) sed does not cover and which has no target anywhere (delete the ref or create the file). Add a plain-text repo-relative-path pattern to lint_broken_refs.py and index _dormant as a source tree.

### AW-13 — Windows task layer hardcodes drive H: (workspaceFolder h:\ml-vol-estimator, H:\all-languages-env.cmd, H:\venv*) with no fallback — every .cmd task fails silently off the GS box

**HIGH · broken · effort: medium · ADJUSTED-CONFIRMED**

**Location:** `skills/_shared/_run.cmd:27` · `skills/GIT/src/git_task.cmd:23` · `skills/MODEL_TRAIN/SKILL.md:163` · `skills/SEARCH/SKILL.md:60` · `skills/PYTHON_PATH/src/resolve.ps1:18` · `ml-vol-estimator.code-workspace:22`

**Evidence:** _run.cmd:27 `call H:\all-languages-env.cmd >nul 2>&1` (fails silently off-box); :31-32 venv probe only `H:\venv%%V\Scripts\python.exe`, else :35 `echo ERROR: No Python venv found in H:\venv*` + :36 `exit /b 1` (diagnostic IS emitted, non-zero). git_task.cmd:24 (not :23) `set "GIT_EDITOR=H:/ml-vol-estimator/skills/GIT/src/noop_editor.cmd"`. resolve.ps1:18 `$fallback='H:\venv311\Scripts\python.exe'` (no PATH fallback, Write-Error+exit1 at :57). MODEL_TRAIN/SKILL.md:163 `run_task("model-train", workspaceFolder: "h:\ml-vol-estimator")`. SEARCH/SKILL.md:60 `H:\venv311\Scripts\python.exe`. Direct-python wrappers (train_task.cmd:20/tail, backtest/ingest/evaluate/feature/notebook/research) hardcode `call H:\all-languages-env.cmd` then `python -m volforecast...` (no venv fallback; python error is visible, not silent). code-workspace:22 `"h:/"` is in additionalReadAccessPaths, NOT a workspaceFolder — folder is `"path": "."`. Contrast: _run.sh:28-44 and resolve.py _find_python_windows() (shutil.which fallback) are portable.

**Why it matters:** The .sh twins correctly derive ROOT from BASH_SOURCE and fall back to src/.venv/python3; the .cmd has no PATH/py-launcher fallback, so on any second checkout every Python-backed run_task dies at venv detection. The H: call error is masked by `>nul 2>&1` and wrappers exit 0, so the agent's only signal is a missing out_file — a silent hang with no diagnostic.

**Recommended fix:** In _run.cmd, guard `if exist H:\all-languages-env.cmd call ...` and add repo-local fallback after the H:\venv probe: derive ROOT via %~dp0..\.. then try `%ROOT%\src\.venv\Scripts\python.exe`, then `where python`, mirroring _run.sh. In the direct-python wrappers (train/backtest/ingest/evaluate/feature/notebook/research) replace bare `python` with the resolved interpreter. In git_task.cmd:24-25 use `%~dp0noop_editor.cmd` (noop_editor.cmd is co-located in skills/GIT/src). Give resolve.ps1 a `Get-Command python` fallback like resolve.py. Drop `workspaceFolder: "h:\ml-vol-estimator"` from SKILL.md run_task examples (single-root workspace resolves it). Note: this does NOT make failures fully silent today — the "missing out_file only" framing should be dropped; diagnostics already print.

### AW-14 — Non-negotiable ML constraints exist in 5-7 copies across 4 layers, the canonical owner is orphaned, and the mandated PurgedKFold import does not exist

**HIGH · architecture · effort: medium · CONFIRMED**

**Location:** `policy/ml-constraints.md:3` · `AGENTS.md:77` · `personas/model-builder.md:20` · `personas/eval-sentinel.md:28` · `.github/instructions/python.instructions.md:46` · `.github/instructions/python.instructions.md:178` · `src/volforecast/utils/cv.py:45`

**Evidence:** ml-constraints.md:3 'always active … cannot be overridden' — sole inbound ref is policy/index.md. Same QLIKE/purged-CV/log-RV/COVID rules restated in AGENTS:77, model-builder:20, eval-sentinel:28, python.instructions:154. python.instructions:46 `from volforecast.utils.time_series import PurgedKFold` — no such module; real class is PurgedKFoldCV at utils/cv.py:45; the embedded impl (178-202) uses purge_gap=22 vs config default 5.

**Why it matters:** Five+ independently-editable copies of the project's hard rules guarantee drift (COVID phrased differently in each); the file whose job is to own them is unreachable. The taught import raises ModuleNotFoundError and the embedded class invites re-implementing a stale-default version, producing inconsistent CV.

**Recommended fix:** Declare AGENTS.md:77-84 the canonical table; reduce persona/instruction copies to 'apply Key Constraints (AGENTS.md)'; wire ml-constraints.md into python.instructions mandated reads or fold its unique detail (purge window >= horizon) and delete. Fix python.instructions:46 to `from volforecast.utils.cv import PurgedKFoldCV` and delete the embedded class.

### AW-15 — memory/INDEX.md token estimates are wrong up to 10.8x, list dead paths, and P0+P1 is 81k tokens vs the 50k cap — the budget lint validates the fiction

**HIGH · context · effort: medium · CONFIRMED**

**Location:** `memory/INDEX.md:33` · `memory/INDEX.md:48` · `memory/INDEX.md:69` · `memory/INDEX.md:114` · `memory/design.md:49` · `workspace/lint/lint_memory_priority.py:112`

**Evidence:** INDEX:48 lgbm-pooled '890' tok vs measured 38,454B≈9,614 (10.8x); :33 project-state '255' vs ~2,510; user.md '280' vs ~859. design.md:49 'P0+P1 ≤50k'; measured P0+P1 md set 325,842B≈81,461t (+trials.yaml ~29,978). INDEX:69 workspace/docs/architecture-audit.md and :114 vol-learning-framework-design.md both MISSING. Lint sums e['tokens'] from INDEX so it passes on fiction.

**Why it matters:** INDEX.md is boot-read every session and is the model's only budget-arithmetic input (AGENTS.md:135 '~60% of context'); with estimates 4-11x low the model can't make sane load decisions, the loaded tier is 63% over its own cap, and two lookup rows dead-end.

**Recommended fix:** Make lint_memory_priority.py compute tokens from bytes/4 and rewrite INDEX's ~Tokens column from measurement; add existence-checks for every INDEX path; demote fat P1s (lgbm-pooled 9.6k, data-audit ~9.9k, user-manual 6.6k) to P2 to get under 50k; delete the two dead workspace rows.

### AW-16 — P0 boot file project-state.md self-contradicts on LSTM status and blockers and is ~40% stale history loaded every session

**HIGH · broken · effort: small · ADJUSTED-CONFIRMED**

**Location:** `memory/research/project-state.md:15` · `memory/research/project-state.md:84` · `memory/research/project-state.md:21` · `memory/research/project-state.md:89` · `memory/person/user.md:44` · `AGENTS.md:55`

**Evidence:** project-state.md:15 'LSTM research line **reopened**' vs :84 'LSTM research line CLOSED (2026-06-22)' (un-annotated stale Key Decision, both in P0 boot file); :21 '**Blocker:** None' vs :89 'Data Ingestion Infrastructure (BLOCKER — blocks L3-L7 feature layers)'. Stale history ~4,032B of 10,038B (~40%): retracted table 759B + IV-sanity 274B + 22 Key Decisions 2,999B. user.md:44-56 ~868B mostly dormant Slang conventions. Combined ~1,225t loaded unconditionally via AGENTS.md:54-56 every session.

**Why it matters:** Every session starts with two direct contradictions about research direction and whether work is blocked (agent may act on either half), plus ~1,220t of dated trial history and parked-Slang conventions loaded unconditionally — wasted and misleading.

**Recommended fix:** In project-state.md: annotate/remove the superseded :84 CLOSED entry (reconcile with :15 reopened), reconcile :21 Blocker field with the :89 BLOCKER scope (e.g. 'None for champion track; data-ingestion blocks L3-L7'), and move the retracted table (40-51), IV-sanity results (53-60), and dated Key Decisions (62-85) to research-journal.md — keep only operative methodology in the boot file. In user.md, collapse 44-55 (dormant Slang/GitLab conventions) to a one-line dormant pointer but PRESERVE line 56 (numbered next-steps + /slash command), an active convention.

### AW-19 — python.instructions.md (3,083 tokens of GS data-access + ML rules) attaches to all 349 .py files including 72 skills/lint scripts, and inlines content it routes to on demand

**HIGH · context · effort: small · ADJUSTED-CONFIRMED**

**Location:** `.github/instructions/python.instructions.md:2` · `.github/instructions/python.instructions.md:8` · `.github/instructions/python.instructions.md:60` · `.github/instructions/python.instructions.md:302`

**Evidence:** applyTo `**/*.{py,ipynb}` (L2) matches 350 tracked .py (277 src, 39 skills, 34 workspace[=16 lint + 15 scripts + 2 presentation + 1 learning]) and 0 tracked .ipynb. Non-src attachment = 73 files (20.9%). File=12,333B≈3,083t. Body is TSDB/Chunk/Marquee/QLIKE/PurgedKFold. L8-16 route to memory/ref/python-{pyslang,tsdb,chunk}.md (all present) + skills/PYTHON_MARKET_DATA/SKILL.md, then L60-148 (2,732B≈683t) re-embed the same chunk_query/TSDB/Marquee examples; Key Rules L302-329 (1,518B≈380t) restate the ref-doc rules — ~1,050t total duplication. pyslang.start() appears 4x (L10,86,305,307); only L86 ties to chunk_query. ERDVOL_PERCENT_STANDARD (L120) vs EDRVOL_PERCENT (L126) — transposed letters + dropped _STANDARD, a wrong-dataset landmine. 
 Narrow applyTo to `src/**/*.py` (drop the dead .ipynb branch); delete the embedded Data Access code blocks (L60-148) and duplicated Key Rules that the file already routes to in memory/ref/; fix EDRVOL_PERCENT->ERDVOL_PERCENT_STANDARD at L126. Add a small env + File-Output-HARD-RULE instruction scoped to `{skills,workspace}/**/*.py` (not just workspace/lint) so skills, lint, scripts, and presentation .py retain the universal write-location/env guidance that src-narrowing would otherwise strip.

**Why it matters:** Per-request: editing skills/_shared/gitlab_auth.py or workspace/lint/design_lint.py attaches ~3,083t about Marquee surfaces and purged CV that can't apply (~21% of tracked .py), and ~1,050t of that duplicates the on-demand refs the file itself routes to — defeating the pointer design.

**Recommended fix:** Restrict attachment away from helper scripts: add a negative/scoped rule or split so skills/**/*.py and workspace/lint/**/*.py get a tiny env+file-output-only instruction instead of the full body. Keep coverage for src/**/*.py (and workspace/scripts data/ML scripts). Delete the L60-148 Data Access code blocks and the duplicated L302-329 Key Rules since the file already routes to memory/ref/*; fix the ERDVOL->EDRVOL_PERCENT_STANDARD dataSetId typo at L120/126; drop the .ipynb glob (0 tracked notebooks). Note: fix's original "Narrow to src/**/*.py" is acceptable since workspace/scripts also don't import data-access, but would drop ML-constraint coverage from analysis scripts.

### AW-20 — yaml-config.instructions.md enum tables are stale vs the live registries it names as source of truth

**HIGH · quality · effort: medium · CONFIRMED**

**Location:** `.github/instructions/yaml-config.instructions.md:53` · `.github/instructions/yaml-config.instructions.md:314` · `src/volforecast/features/implied_correlation.py:1` · `workspace/configs/_CANONICAL_EXAMPLE.yaml:1`

**Evidence:** Registry has 13 @register_feature_layer names incl. implied_correlation; the layer table (55-68) lists 12, omitting it (also absent from _CANONICAL_EXAMPLE.yaml). Model section omits ~10 @register_model names (blend, gnn, har_cj_iv_*, sharq_cj_iv_*, ridge/lasso_har_iv_ratevol). No CI regenerates these tables.

**Why it matters:** The file presents these as 'Valid Enum Values', so agents will treat registered models/layers as invalid, refuse them, or 'correct' working configs. Drift proves the file's own Schema Maintenance Rule is unenforced.

**Recommended fix:** Add the missing layer+models to the tables and _CANONICAL_EXAMPLE.yaml; add a CI step regenerating the enum lists from the registries and failing on diff.

### AW-22 — Six of 14 policy files are orphaned from all loading surfaces, including two that self-declare mandatory/always-active

**HIGH · broken · effort: medium · ADJUSTED-CONFIRMED**

**Location:** `policy/preflight-gates.md:3` · `policy/ml-constraints.md:3` · `policy/operating-principles.md:1` · `policy/interaction_model.md:1` · `policy/communication_protocol.md:1` · `policy/implementation_boundary.md:1`

**Evidence:** preflight-gates.md:3 "These fire before any other logic. Never skip, never defer." and ml-constraints.md:3 "always active and cannot be overridden" both verified. No always-on injection (AGENTS.md/copilot-instructions.md) or on-demand prompt/persona/skill/applyTo file loads any of the 6; grep confirms zero forward loading refs. The only forward reference is policy/index.md (lines 20-22), itself linked from AGENTS.md:143 as "Full docs in policy/index.md" — a passive pointer that surfaces one-line descriptions, not the gates/formulae. So the substantive content (preflight gates 2-6, QLIKE LaTeX formula, purge-window>=horizon, per-experiment checklist) never reaches context. Mitigation: AGENTS.md:79-86 already restates 6 of 8 ml-constraints rules and boot protocol (54-60) covers gate 1, so the marginal unreachable content is the operative detail plus operating-principles (near-100% duplicated in AGENTS.md:145-158 = dead maintenance weight) and the Slang-specific secexpr --safe gate that silently never fires for .s work.

**Why it matters:** The gate design silently never executes: nothing instructs Copilot to read these files. ml-constraints' operative detail (purge window >= horizon, QLIKE formula, per-experiment checklist) never reaches the model; only AGENTS.md one-liners do. operating-principles is ~100% restated in AGENTS.md, so it is dead maintenance weight.

**Recommended fix:** For each orphan: wire it from the relevant always-on row (as the TDD row links working-agreements.md) or fold unique content into AGENTS.md and delete the file. Fold preflight gates 5-6 into copilot-instructions if they must be unconditional.

### AW-24 — /study, /quiz, /teach load a 194KB YAML graph + 22KB state (~54k tokens per session) despite touching a handful of nodes

**HIGH · context · effort: medium · CONTESTED**

**Location:** `.github/prompts/study.prompt.md:11` · `.github/prompts/quiz.prompt.md:9` · `memory/INDEX.md:112`

**Evidence:** study/quiz bullets load workspace/learning/graph.yaml (194,412B≈48,603t) and mastery-state.json (21,984B≈5,496t). INDEX:112 understates graph.yaml as 26,530 tokens (1.8x low).

**Why it matters:** Per session ~54k tokens (~27% of a 200k window) consumed before the first question, though a session touches a few of 28+ nodes; mastery-state already encodes which are overdue/frontier so the full graph is never needed at once.

**Recommended fix:** Add a selector (skills/study src/select_nodes.py reading mastery-state.json) emitting only due+frontier nodes with their subtree to workspace/tmp/, and load that instead of graph.yaml; or shard graph.yaml per domain. Est ~40k tokens/session.

### AW-25 — Prompt runbooks fork the skills they shadow: backtest/feature/research prompts re-implement workflows with drifted parameters and never reference the skill

**HIGH · architecture · effort: medium · ADJUSTED-CONFIRMED**

**Location:** `.github/prompts/backtest.prompt.md:22` · `skills/BACKTEST/SKILL.md:104` · `.github/prompts/feature.prompt.md:26` · `.github/prompts/research.prompt.md:17` · `workflows/research.md:1`

**Evidence:** backtest.prompt.md:22 "transaction costs (default: 5 bps round-trip)" diverges from BACKTEST/SKILL.md:61-65 & 106-110 (spread_bps 5 + commission_per_contract 1.25 + slippage_bps 2). backtest.prompt.md never links the skill: grep 'SKILL'=0 (the finding's "grep=0" is only true for the skill link; grep -ci 'backtest'=4 as the concept word). feature.prompt.md:26 routes to src/ml_vol_estimator/features/ which does NOT exist in the tracked tree — package renamed to src/volforecast/features/ (har.py, asymmetry.py present); status.prompt.md carries the same stale name; prompt never links FEATURE_BUILD/SKILL.md (which runs run_task "feature-build"). research.prompt.md:11 DOES link workflows/research.md but lines 17-27 duplicate a 7-step protocol that omits the workflow's mandatory Hypothesis Card / FOCUS gate (workflows/research.md:56-67). data-audit.prompt.md:6 and git-commit.prompt.md:7 are single-link thin dispatchers, confirming two coexisting patterns.

**Why it matters:** Two divergent specs of the same procedure: /backtest simulates with a different cost model than the skill implements so results differ by entry path; /research skips the workflow's FOCUS validation. data-audit.prompt.md and git-commit.prompt.md are correct thin dispatchers, so two incompatible prompt patterns coexist with no rule.

**Recommended fix:** Rewrite backtest/feature/research prompts as thin dispatchers (mode sentence + persona + link to the owning SKILL.md/workflow) and defer all parameters to the skill. Immediately fix the broken path: replace src/ml_vol_estimator/features/ with src/volforecast/features/ in feature.prompt.md:26 and status.prompt.md. Add a "prompts are dispatchers, never procedure copies" rule to skills/design.md (currently 121 lines, no such rule).

### AW-G27 — Coverage gate (--cov-fail-under=30) exists only in CI; ./vol test/test-all and pyproject enforce no coverage at all

**HIGH · broken · effort: small · ADJUSTED-CONFIRMED**

**Location:** `src/pyproject.toml:84` · `vol:218` · `vol:224` · `.github/workflows/ci.yml:40`

**Evidence:** CI runs `pytest tests/ --cov=volforecast --cov-report=term-missing --cov-fail-under=30` (ci.yml:40) — the ONLY coverage gate in the tracked tree (grep -c cov-fail = 1). src/pyproject.toml:84 addopts = "--import-mode=importlib --ignore=tests/slow" (no --cov). `./vol test` → `pytest tests/ -m "not slow" "$@"` (vol:218); `./vol test-all` → `pytest tests/ "$@"` (vol:224) — neither adds coverage. The documented pre-commit check is at vol:98 ("Default agent inner-loop. Run `test-all` before committing."), not vol:99. NOTE: the "AW-06" gate ID cited in the original finding does not exist anywhere in the tracked tree.

**Why it matters:** The agent inner loop and the documented pre-commit check (help vol:99 'Run ./vol test-all before committing') produce ZERO coverage measurement, so a drop below the AW-06 30% gate is invisible locally and only fails in CI. Identical code: green locally, red in CI.

**Recommended fix:** Move the gate into src/pyproject.toml so all surfaces share it, e.g. addopts += " --cov=volforecast --cov-fail-under=30". Caveat (already noted in finding): `./vol test` runs a subset (-m "not slow"), so an addopts-level --cov-fail-under would measure lower coverage on the fast loop and could false-fail; give ./vol test an opt-out (separate marker/arg) while ./vol test-all and CI enforce the gate.

### AW-G28 — CI installs --dev only, not the `ml` extra, so every importorskip'd ML model test is silently SKIPPED in CI but RUN by ./vol test-all

**HIGH · broken · effort: trivial · CONFIRMED**

**Location:** `.github/workflows/ci.yml:28` · `vol:51` · `src/tests/unit/test_lightgbm.py:9` · `src/tests/unit/test_xgboost.py:9`

**Evidence:** CI `uv sync --dev` (ci.yml:28) omits [project.optional-dependencies].ml (lightgbm/xgboost/optuna/shap). ./vol `uv sync --frozen --extra ml` (vol:51). Tests hard-gate on those deps: `lgb = pytest.importorskip("lightgbm")` (test_lightgbm.py:9), `xgb = pytest.importorskip("xgboost")` (test_xgboost.py:9) across 5+ files.

**Why it matters:** importorskip turns a missing dep into a SKIP, not a failure. So CI never executes lightgbm/xgboost/optuna/shap model tests — CI can go green on broken ML model code that ./vol test-all would fail on, and the --cov-fail-under=30 denominator is computed over a different executed test set than the agent runs locally.

**Recommended fix:** Add `--extra ml` (or a CI-appropriate extra) to the CI `uv sync` step so CI exercises the same test set as ./vol, OR make the ML tests hard-required (drop importorskip) so a missing extra fails loudly instead of silently skipping.

## Severity: Medium (40 findings) — meaningful, localized

### AW-G6 — memory/ref/vol-cli.md claims to "mirror ./vol help" but omits 13 of 33 vol commands, incl. test-all and the whole tick/iv/micro ingest family

**MEDIUM · context · effort: small · CONFIRMED**

**Location:** `memory/ref/vol-cli.md:13` · `AGENTS.md:214` · `vol:81`

**Evidence:** vol-cli.md:13 "This file mirrors `./vol help`". Its tables list ~19 commands; vol has 33 case arms (grep -c = 33). Missing: test-all, notebook, ingest-ohlcv/ticks/iv/xasset/corr/micro/edrvs, kvar, cache-status, cache-clear, present. AGENTS.md:214 cites it as the "full reference".

**Why it matters:** Per-invocation: an agent that follows the always-on AGENTS.md:214 pointer to this ~3.7KB "full reference" is misled into believing ingest-ticks/iv/micro, kvar, cache-clear, present and even the mandated pre-commit test-all are not vol capabilities. It omits the exact long-running ingest commands the workflow needs. Escape hatch (line 13 "run ./vol help to validate") only partly mitigates.

**Recommended fix:** Regenerate the tables directly from the vol help heredoc (vol:82-210) so all 33 commands appear, or drop the "mirrors ./vol help" claim and mark it an explicit curated subset. Add a check that fails if a vol case arm has no vol-cli.md row.

### AW-G10 — All 43 run_task skill tasks live only in ml-vol-estimator.code-workspace; the folder-opened coding agent has no tasks.json, so zero task labels resolve

**MEDIUM · broken · effort: medium · ADJUSTED-CONFIRMED**

**Location:** `ml-vol-estimator.code-workspace:51` · `ml-vol-estimator.code-workspace:55` · `.vscode/settings.json:1` · `AGENTS.md:174`

**Evidence:** Core gap real: tasks live only in the multi-root .code-workspace, with no folder-scoped .vscode/tasks.json, so labels won't resolve when the repo is opened as a folder (coding-agent path). BUT three facts soften it: (1) the designed-for consumer is VS Code Chat opening the .code-workspace on the GS Windows box, where all 43 resolve — memory/ref/vscode-tasks.md itself anchors every rule to "ml-vol-estimator.code-workspace". (2) A fallback is already documented — vscode-tasks.md:96 E3: "Use create_and_run_task when run_task can't find predefined tasks — Fallback for multi-workspace .code-workspace task definitions". (3) The coding-agent path is a "possibly" consumer, not confirmed. AGENTS.md:174 does not contain run_task; it is the "Available Skills" table.

**Why it matters:** Workspace-file (.code-workspace) tasks are loaded by VS Code ONLY when that file is opened as a multi-root workspace. The async coding agent clones the repo and opens it as a folder, so it never parses ml-vol-estimator.code-workspace. With no .vscode/tasks.json, none of the 43 run_task labels exist for it. Since AGENTS.md drives skills through these task wrappers, the entire skill-invocation surface is unreachable for the coding agent.

**Recommended fix:** Mirroring the 43 into .vscode/tasks.json is NECESSARY-BUT-NOT-SUFFICIENT: the wrappers are GS/Windows-bound — lint_vscode_tasks.py W1 requires `call H:\all-languages-env.cmd` and W2/W6 assume `H:\venv*` — so a Linux cloud coding agent still can't execute them even with resolvable labels. The real correction: (a) state in AGENTS.md that the run_task/`close:true` model is VS-Code-Chat-on-GS-Windows-only, (b) if coding-agent support is intended, add a folder-scoped tasks.json AND a non-task, env-portable execution path, otherwise the always-on AGENTS.md HARD RULE (line 157: never fall back to run_in_terminal) silently strands the agent.

### AW-G11 — Skill bootstrap wrappers assume GS-mapped H: drive (Windows) or a prebuilt src/.venv+nix (Linux); neither exists on a stock runner, so skill Python cannot execute even if invoked by path

**MEDIUM · broken · effort: large · ADJUSTED-CONFIRMED**

**Location:** `skills/_shared/_run.cmd:27` · `skills/_shared/_run.cmd:32` · `skills/_shared/_run.sh:33` · `skills/_shared/_run.sh:47`

**Evidence:** Confirmed exact: _run.cmd:27 `call H:\all-languages-env.cmd >nul 2>&1`; :31-32 loop `for %%V in (315 314 313 312 311 310 39 38)` / `if exist "H:\venv%%V\Scripts\python.exe"`; :35 `No Python venv found in H:\venv*`. _run.sh:33 `if [[ -f "${ROOT}/src/.venv/bin/python" ]]`; :47 `source "${SHARED_DIR}/nix_ld.sh"`. Counter-evidence: nix_ld.sh:8 `if [[ -z "${LD_LIBRARY_PATH:-}" && -n "${PY:-}" ]]` and :10 `if [[ "$_PY_STORE" == /nix/store/* ]]` — already no-ops off-nix. Invocation is local: CANVAS SKILL.md:212 `run_task("canvas", workspaceFolder: "h:\ml-vol-estimator")`; python-setup.md:78-84 documents src/.venv exists on Linux Coder. No copilot-setup-steps.yml in tracked tree (glob empty).

**Why it matters:** The coding agent's Ubuntu runner has no H: drive and no pre-created src/.venv (that venv is built by `./vol`, which itself can't run — see BLOCKER 1). _run.cmd is Windows-only and hardwired to the GS environment; _run.sh will fall through to bare python3 but then sources nix_ld.sh and runs skill code that targets GS-internal services (SECDB/Slang/Marquee/GitLab) unreachable from the cloud. So the skill compute layer is ~0% operable without provisioning.

**Recommended fix:** Do NOT strip H: hardcodes from _run.cmd — vscode-tasks.md W1/W6 mandate them and removal breaks the working GS-desktop consumer. nix_ld.sh needs no change (already guarded off-nix). Instead: (a) document that skill wrappers are GS-environment-only (Windows H: desktop or Linux Coder src/.venv), invoked via VS Code run_task locally, never on a cloud runner; (b) if the Copilot cloud coding-agent is a real consumer, note explicitly that the entire skill layer is inoperable there — not for lack of a venv but because all skills target unreachable *.gs.com services; provisioning src/.venv would not help. The genuine gap is missing documentation of the two supported execution environments, not a broken bootstrap.

### AW-G12 — AGENTS.md and copilot-instructions.md give contradictory terminal rules that livelock the coding agent: re-run the (nonexistent) run_task forever, never use a raw terminal

**MEDIUM · broken · effort: small · ADJUSTED-CONFIRMED**

**Location:** `AGENTS.md:157` · `.github/copilot-instructions.md:30` · `.github/copilot-instructions.md:33` · `.github/copilot-instructions.md:34`

**Evidence:** AGENTS.md:143 delegates terminal rules to copilot-instructions.md, yet AGENTS.md:157 adds a global run_task-primary bullet. copilot-instructions.md §3 (:30 './vol exec', :33 'run_in_terminal', :39 'kill_terminal') never mentions run_task; grep -c run_task in copilot-instructions.md = 0. The prompts scope run_task to lint labels (lint.prompt.md:13, lint-workspace.prompt.md:55), but no .vscode/tasks.json is tracked. Contradiction is real but narrow: :157's 'with a raw command' qualifier and both docs' shared 'no raw terminal' rule mean run_in_terminal("./vol exec") is valid under both.

**Why it matters:** run_task and run_in_terminal are VS Code Chat tools; for the async coding agent run_task never resolves (BLOCKER 2), so AGENTS.md:157 instructs it to keep re-running a task that will never work and explicitly bars the only working escape hatch. Simultaneously copilot-instructions.md:33 assumes run_in_terminal exists and is used. The two documents disagree on the execution mechanism, and neither branch is valid on the cloud runner.

**Recommended fix:** Reconcile the single AGENTS.md:157 bullet with copilot-instructions.md §3: either drop the run_task-primary language or scope it to the predefined lint tasks (as the prompts already do), and state run_in_terminal + ./vol exec/bg as the one canonical compute mechanism. Since AGENTS.md:143 already delegates terminal rules to copilot-instructions.md, :157 should not introduce a competing tool.

### AW-G14 — No MCP config, no .github/agents, no .github/chatmodes: the coding agent has no alternative tool surface, and the workspace file's virtual slang:/ folders confirm desktop-only design

**MEDIUM · broken · effort: medium · ADJUSTED-CONFIRMED**

**Location:** `ml-vol-estimator.code-workspace:5` · `ml-vol-estimator.code-workspace:22` · `ml-vol-estimator.code-workspace:24`

**Evidence:** Tracked root file ml-vol-estimator.code-workspace declares VS Code desktop-only virtual folders "uri":"slang:/" (L5), "slang-temporary:/" (L9), "slang-favorites:/" (L13) plus github.copilot.chat.additionalReadAccessPaths:["h:/"] (L21-23) and commandAllowlist terminal:["*"] (L24) — all interactive-VS-Code constructs a cloud coding agent never consumes. Glob confirms no .github/agents or .github/chatmodes dirs; git ls-files has no MCP config (only abstract "direct action → MCP → delegation" prose at AGENTS.md:147). Always-on copilot-instructions.md (rules 2,3,8) and AGENTS.md:157 mandate ./vol/run_task and forbid run_in_terminal "with zero exceptions", so a cloud coding agent that cannot reach the GS Linux Coder Workspace has no MCP/agents fallback for RUNNING the skill/compute layer. Nuance: direct file read/edit (first in AGENTS.md:147 lightest-path) still works, so this is loss of the executable-tool surface, not all capability; and it is conditional on BLOCKER 1 (./vol) and BLOCKER 2 (run_task).

**Why it matters:** With run_task dead (BLOCKER 2) and ./vol dead (BLOCKER 1), an MCP server would be the only remaining programmatic capability — but none is configured, so the coding agent falls back to raw shell, which the instructions forbid. The slang:/ virtual folders and h:/ read-access in the workspace file are non-filesystem GS-desktop constructs that reinforce that this config was authored for interactive VS Code on a GS box, never the cloud runner.

**Recommended fix:** Decide whether the Copilot coding agent is a supported consumer. If yes, give it an actually-runnable path (an MCP server, or a folder-scoped .vscode/tasks.json plus a provisioned Linux env with ./vol on PATH) since the tasks currently live only inside the .code-workspace file. If no, add one line to the always-on AGENTS.md/copilot-instructions.md scoping the coding-agent out, so the ./vol- and run_task-mandating rules stop advertising an executable workflow the cloud runner cannot perform. Note the config still permits direct file edits regardless.

### AW-G15 — data-audit.md Appendix marks tsdb.py OHLCV/treasury/fx/commodity fetchers TODO, but they're implemented in src and called 'Implemented' elsewhere in the same doc

**MEDIUM · context · effort: trivial · CONFIRMED**

**Location:** `workspace/docs/data-audit.md:937` · `workspace/docs/data-audit.md:938` · `workspace/docs/data-audit.md:84` · `workspace/docs/data-audit.md:644` · `src/volforecast/data/tsdb.py:142` · `src/volforecast/data/tsdb.py:210`

**Evidence:** Appendix (line 937-940): "tsdb.py | fetch_daily_ohlcv(...) | **TODO**" and "use the direct query snippets ... until the volforecast.data wrappers are implemented" (946). But src/volforecast/data/tsdb.py:142 `def fetch_daily_ohlcv(`, :210 fetch_treasury_yields, :256 fetch_fx_rates, :301 fetch_commodity_prices all exist; Layer-4 table (644-648) marks treasury_slope/fx_vol/commodity_vol 'Implemented'; boilerplate (84) imports all four.

**Why it matters:** data-audit.md loads as P1 (~7350 tok) on 'Data queries, feature implementation' (INDEX.md:53). The stale TODO tells the agent to hand-write verbose inline TSDB query snippets or re-implement already-shipped wrappers on every data task. Per-invocation waste of the largest P1 doc.

**Recommended fix:** Flip Appendix rows 937-940 to Implemented and delete the 'use direct snippets until wrappers exist' fallback (946); reconcile the marquee/iv module names (iv_ingest.py vs marquee.py).

### AW-G16 — memory/ref/vol-cli.md claims to mirror ./vol help but documents only 19 of the 33 vol subcommands

**MEDIUM · context · effort: small · CONFIRMED**

**Location:** `memory/ref/vol-cli.md:13` · `vol:82` · `vol:167` · `vol:178` · `vol:324`

**Evidence:** vol-cli.md:13 "This file mirrors `./vol help`. If commands seem wrong or missing, run `./vol help`". vol case-dispatch has 33 subcommands; grep of vol-cli.md for present|kvar|cache-status|cache-clear|ingest-iv|ingest-micro|test-all = 0. Omitted 14: test-all, notebook, ingest-ohlcv/ticks/iv/xasset/corr/micro/edrvs, kvar, present, cache-status, cache-clear (+help).

**Why it matters:** vol-cli.md is P1 'vol wrapper command lookup' (INDEX.md:96, ~540 tok). An agent looking up e.g. `present`, `kvar`, or the primary `ingest-iv` finds nothing and concludes it doesn't exist — falling back to raw `python -m volforecast ...` or skipping the step. The self-labelled 'mirror' is silently 42% incomplete.

**Recommended fix:** Regenerate vol-cli.md from the vol help heredoc (vol:82-210), or drop the 'mirrors ./vol help' guarantee and mark it a curated subset.

### AW-17 — Research journal is forked: memory/INDEX.md routes continuity to a copy 8 weeks staler than the one every workflow writes

**MEDIUM · organization · effort: small · ADJUSTED-CONFIRMED**

**Location:** `memory/INDEX.md:39` · `memory/research/research-journal.md:15` · `workflows/research.md:124` · `workflows/bootup.md:19` · `.github/prompts/research.prompt.md:14`

**Evidence:** INDEX.md:39 routes 'Research session start, continuity' to memory/research/research-journal.md (11,332B; newest entry 2026-06-03, frontmatter updated:2026-06-03). Live journal workspace/research/research-journal.md (33,736B, ~3x; newest 2026-07-01) is written by workflows/research.md:124, read by workflows/bootup.md:19 AND .github/prompts/research.prompt.md:14. So INDEX:39 is the lone pointer to the staler copy (~4-week gap), reached only via always-on AGENTS.md:57 boot + INDEX's P1 load-on-cue routing — not a per-request always-on cost. Note: 2026-05-08 is merely the last heading by file position; the file is not chronologically ordered.

**Why it matters:** Two files claim to be the same journal; an agent following the boot-loaded INDEX resumes from state ~2 months behind the live journal. Explains the 'trials 036-073 unjournaled' symptom — they are journaled, in the other file.

**Recommended fix:** Repoint memory/INDEX.md:39 to workspace/research/research-journal.md and convert memory/research/research-journal.md to a ~15-line pointer card (mirroring how memory/research/weekly-progress.md points to its workspace twin via a 'Location:' line + source frontmatter). Verify no break: memory/research/README.md:45 lists the journal (update its blurb); memory weekly-progress.md 'relates: [research-journal]' still resolves.

### AW-18 — Six flat-file skills plus an orphan ssp_helpers.py sit at skills/ root, violating the skill contract, missing from skills/INDEX.md, and invisible to both skill linters

**MEDIUM · organization · effort: medium · ADJUSTED-CONFIRMED**

**Location:** `skills/quiz.md:1` · `skills/teach.md:1` · `skills/study.md:1` · `skills/learning-status.md:1` · `skills/expand-learning-graph.md:1` · `skills/weekly-learning-goals.md:1` · `skills/ssp_helpers.py:1` · `skills/design.md:35` · `workspace/lint/lint_skills_structure.py:89`

**Evidence:** design.md:35 "One directory per skill. Name: UPPER_SNAKE_CASE" vs 6 lowercase flat files at skills/ root (quiz.md 6483, teach.md 6491, study.md 5475, learning-status.md 3603, expand-learning-graph.md 5759, weekly-learning-goals.md 4591 = 32,402B). INDEX.md = 48 skill rows (all 48 UPPER_SNAKE dirs; zero flat files). policy/implementation_boundary.md:24 "Skill system (54 skills)" roster = 48 dirs + the 6 lowercase files → three authorities disagree. Both linters exclude the flat files: lint_skills_structure.py:89 `if not skill_path.is_dir(): continue` (ROOT_ONLY_FILES={"INDEX.md"} only, so quiz.md passes _is_skill_folder then is skipped at is_dir); validate_skills.py:240 iterates `entry.is_dir() and (entry/"SKILL.md").is_file()` → 32KB skips 100% of structure/content validation. skills/ssp_helpers.py = 5,200B, 0 tracked references (design.md anti-pattern #5 "Script without SKILL.md"). NUANCE the finding omits: the 6 flat files ARE wired to .github/prompts/{quiz,teach,study,learning-status,expand-learning-graph,weekly-learning-goals}.prompt.md, each referencing skills/<name>.md and loading on-demand — so they are reachable via slash commands, just missing from the skills registry and unlinted; ssp_helpers.py has no such wiring.

**Why it matters:** Three authorities disagree on the skill roster (INDEX 48, boundary 54, contract dirs-only). The flat skills are undiscoverable in the registry and unlinted; ssp_helpers.py is the design.md 'script without SKILL.md' anti-pattern.

**Recommended fix:** Reconcile the roster across all three authorities: either (a) convert the 6 learning guides to UPPER_SNAKE dirs with SKILL.md + add INDEX rows, or (b) formally sanction a flat prompt-guide variant in design.md §3 and teach both linters to validate lowercase *.md skill files (frontmatter/size). Fix implementation_boundary.md:24 to match whatever roster is chosen (currently 54 vs INDEX 48). Delete skills/ssp_helpers.py (0 refs) or move it under a skill's src/ with a governing SKILL.md.

### AW-G19 — user-manual.md hardcodes Linux /home/developer paths and the vol wrapper is bash/nix-only — the documented CLI loop silently breaks off GS-Linux

**MEDIUM · context · effort: small · CONFIRMED**

**Location:** `workspace/docs/user-manual.md:405` · `workspace/docs/user-manual.md:406` · `vol:1` · `vol:342` · `vol:44`

**Evidence:** user-manual.md:405 example output "Created: /home/developer/ml-vol-estimator/workspace/configs/...". vol:1 `#!/usr/bin/env bash`; vol:342 `setsid bash -c`; vol:38-44 `nix-store --query`; vol:56 `sed -i`; vol:60 `source ${SRC}/.venv/bin/activate`. No OS guard.

**Why it matters:** user-manual.md is P1 (~5420 tok) for 'CLI commands, vol run' (INDEX.md:54). Both the manual and the wrapper assume a GS Coder/nix Linux box; on the Windows restored snapshot (and any non-nix host / the H: skill layer) every documented `./vol ...` invocation fails at setsid/nix-store/venv-activate with no fallback, and the /home/developer path is wrong even on other Linux roots. This is the env assumption that silently breaks the workflow.

**Recommended fix:** State the Linux+nix requirement in the manual; replace the hardcoded /home/developer output with a ${ROOT}-relative placeholder; consider an OS guard or PowerShell shim for the Windows dev loop.

### AW-21 — A 14-check agentic-config lint suite has no deterministic trigger (CI/pre-commit both skip it) and the tracked tree currently fails it 3/14

**MEDIUM · architecture · effort: small · ADJUSTED-CONFIRMED**

**Location:** `.github/workflows/ci.yml:14` · `.pre-commit-config.yaml:3` · `.github/copilot-instructions.md:52` · `workspace/lint/lint_all.py:1` · `AGENTS.md:58` · `.github/prompts/gsvivs-audit.prompt.md:155`

**Evidence:** lint_all.py registry = 14 checks; `python workspace/lint/lint_all.py` -> "FAILED (3/14): design rules, broken refs, vscode md compat" (2.4s). lint_broken_refs.py (scans 178 tracked .md) -> "FAIL: 2 broken reference(s)": AGENTS.md:58 md-link -> workspace/tmp/session-handoff.md (runtime file, never in clean tree) and .github/prompts/gsvivs-audit.prompt.md:155 -> workspace/docs/gsvivs_iv_improvement_plan.md. NOTE the gsvivs target is not missing—it exists at workspace/research/gsvivs_iv_improvement_plan.md (wrong dir in the link). design_lint fails on tracked top-level `docs/` (git-tracked docs/superpowers/*) plus snapshot dirs. Only invocation path is .github/prompts/lint-workspace.prompt.md (on-demand slash command); CI push trigger is [main,develop] but repo branch is master/presentation so push CI never fires either.

**Why it matters:** Every governance rule the linters encode (broken refs, design rules, INDEX completeness) is enforced only if a human volunteers /lint-workspace, so violations (e.g. the stale _dormant links) accumulate silently. AGENTS.md:58's md-link existence-check guarantees a permanent broken-refs FAIL, destroying the gate's signal.

**Recommended fix:** Add a CI job running `python workspace/lint/lint_all.py` (stdlib-only) scoped to the tracked tree, and fix the push trigger (currently [main,develop]; repo branch is master). To actually reach a green state you must fix ALL three current failures, not just AGENTS.md:58: (1) broken refs — backtick the AGENTS.md:58 session-handoff link AND correct gsvivs-audit:155 to workspace/research/gsvivs_iv_improvement_plan.md; (2) design rules — resolve the tracked top-level `docs/` entry (move under workspace/ or whitelist it); (3) vscode md compat. Converting only AGENTS.md:58 leaves the gate red.

### AW-G22 — gnn feature-stack configs break at load when torch-geometric is absent; doc lists neither `gnn` nor its `node_attention` output

**MEDIUM · broken · effort: small · ADJUSTED-CONFIRMED**

**Location:** `workspace/configs/trial_068_gnn_standalone.yaml:74` · `workspace/configs/trial_068_gnn_standalone.yaml:75` · `workspace/configs/trial_070_gnn_feature_stack_xgboost.yaml:90` · `src/volforecast/registry.py:44` · `src/volforecast/pipeline/runner.py:1509`

**Evidence:** Doc (yaml-config.instructions.md, applyTo workspace/configs/**): grep gnn=0, node_attention=0; model.name Deep list l80=lstm,tcn only; outputs table l223-230 omits node_attention though gnn.py:626 valid_outputs={"prediction","node_attention"} and gnn.py:181 registers "gnn". Runtime mechanism corrected: registry.py:44 `import volforecast.models.gnn` only pulls gnn.py top-level torch/torch.nn; torch_geometric imported lazily (gnn.py:104 etc). So torch-geometric absence does NOT drop gnn from MODEL_REGISTRY and does NOT trigger runner.py:1509 "not in registry"; it surfaces as a raw torch_geometric ImportError deeper during GNN construction/training. The registry.py:45 comment "torch-geometric not installed" is itself misleading (it catches missing torch).

**Why it matters:** On any environment without torch-geometric (a heavy optional dep) `gnn` is silently absent from MODEL_REGISTRY, so both gnn configs hard-fail at fold setup — an env assumption that breaks the workflow with no upfront signal. Separately, the instruction doc's model.name list (lines 72-81) omits `gnn` and its feature_stack.outputs table (lines 223-230, only prediction/attention_entropy/attention_peak_time/embedding) omits `node_attention`, so an agent validating these configs against the doc would wrongly flag valid values.

**Recommended fix:** Doc: add `gnn` (Deep/graph family, note requires torch-geometric extra) and `node_attention` to the enum tables — real and worth doing. Runtime: the accurate remedy is to fix the misleading registry.py:45 comment and, if actionable errors are wanted, lazy-guard the torch_geometric import to raise a message naming the missing extra — but do NOT claim the failure occurs at the runner.py:1509 registry check; it does not when torch is present.

### AW-23 — All 34 slash prompts pin premium 'Claude Opus 4.6' (incl. read-only dashboards and 161-byte stubs); the string is duplicated 75x with no lint

**MEDIUM · optimization · effort: small · ADJUSTED-CONFIRMED**

**Location:** `.github/prompts/status.prompt.md:3` · `.github/prompts/learn.prompt.md:3` · `.github/prompts/git-commit.prompt.md:4` · `.github/prompts/kill-orphans.prompt.md:3` · `.github/copilot-instructions.md:72` · `workflows/execute.md:35`

**Evidence:** grep -c 'model:' across .github/prompts/*.prompt.md = 34/34 pin 'Claude Opus 4.6'. Total 'Opus' substring across tracked tree (.github, AGENTS.md, workflows, policy, skills, memory) = 76 (34 pins + 42 prose), not 75. Smallest stub = learn.prompt.md (161 bytes, body is two backtick refs); status.prompt.md is 1848 bytes and is genuinely read-only ('read-only synthesis. Do not modify any files'). copilot-instructions.md:72 and AGENTS.md:23 scope the Opus mandate to subagents only — top-level command pins are unmandated. No lint module (17 in workspace/lint/) checks prompt frontmatter model values; design_lint.py:1155 scans .github/prompts only for broken markdown links. Prompt files are on-demand, so cost is per-command-invocation, not per-request context.

**Why it matters:** Opus-class requests bill at the highest premium multiplier; base-tier is behaviorally equivalent for /status, /git-commit, /learn, /kill-orphans etc. A model rotation needs 34+41 coordinated edits or the pins go stale and silently fall back to the session model, defeating the pinning intent.

**Recommended fix:** Keep the Opus pin on reasoning workflows. For the mechanical/read-only set (status, progress, learn, bootup, lightweight, learning-status, quiz, teach, study, git-commit, gitlab-search, glimpse, kill-orphans, data-audit, slop-cleaner, lint) delete the model: line (inherit session model) or point to a base picker. Add a lint check (extend design_lint.py which already enumerates .github/prompts) asserting every prompt's model: value equals one shared constant, so a model rotation is a single edit and stale pins that silently fall back to the session model are caught.

### AW-G23 — _CANONICAL_EXAMPLE.yaml violates its own Schema Maintenance Rule: missing conditional_duan, gnn, embargo, implied_correlation

**MEDIUM · context · effort: medium · CONFIRMED**

**Location:** `workspace/configs/_CANONICAL_EXAMPLE.yaml:1` · `.github/instructions/yaml-config.instructions.md:12` · `.github/instructions/yaml-config.instructions.md:316` · `src/volforecast/config.py:463` · `src/volforecast/config.py:183`

**Evidence:** grep -c over the 19,438B canonical: conditional_duan=0, gnn=0, implied_correlation=0, embargo=0. Yet config.py:463 defines `conditional_duan`, config.py:183 defines CVConfig `embargo` (Phase 2.8), gnn.py:181 `@register_model("gnn")`, implied_correlation.py:66 `@register_feature_layer("implied_correlation")`.

**Why it matters:** The doc bills the canonical as 'Fully-commented reference showing ALL fields' (line 12) and the Maintenance Rule (lines 316-322) mandates updating it on every new @register_model / @register_feature_layer / config.py field. Four live schema additions never propagated, so the file agents are told to copy-and-modify is stale — the single source of truth silently under-specifies the schema. This instruction file attaches on every workspace/configs/** edit, so the gap misleads each config-authoring request.

**Recommended fix:** Add commented sections to the canonical for conditional_duan (dict), cv.embargo, the gnn model line, and implied_correlation; or add a CI check asserting the canonical loads and that every registry key / config.py field appears in it.

### AW-G24 — Instruction doc's Optional Fields / enum tables omit real top-level schema: conditional_duan, feature_selection, blend, cv.n_splits, cv.embargo

**MEDIUM · context · effort: small · ADJUSTED-CONFIRMED**

**Location:** `.github/instructions/yaml-config.instructions.md:29` · `workspace/configs/trial_068_conditional_duan.yaml:1` · `workspace/configs/trial_063_shap_feature_selection.yaml:1` · `workspace/configs/trial_072_blend_xgb_lstm_h1.yaml:1` · `workspace/configs/baseline_har.yaml:21` · `src/volforecast/config.py:463`

**Evidence:** Doc tables omit all five (conditional_duan/feature_selection/n_splits=0; blend=only regime_blend @79; embargo only in purge_gap prose @35, not 36). Configs confirmed: trial_068:65, trial_063_shap:74, trial_072:46+48, n_splits @baseline_har:21/_CANONICAL:223/trial_063_hpo:84. config.py: conditional_duan @463, CVConfig fields n_splits @178 + embargo @183, strict **-unpack @660. Caveat: the doc directs agents to _CANONICAL_EXAMPLE.yaml, which DOES document feature_selection (258-266) and cv.n_splits (223) — so guidance is nonzero for those two. conditional_duan, the `blend` model+section, and cv.embargo are absent from both the doc and the canonical example. embargo is used by no config (valid-but-unused field).

**Why it matters:** The Optional Fields table (lines 29-50) and model.name list are the schema reference agents edit against, injected per config edit via applyTo `workspace/configs/**`. Five real fields/sections in active configs are undocumented, so an agent asked to add e.g. conditional_duan or a blend model has zero schema guidance and may delete or mis-key them. config.py parses these via **-unpacking (CVConfig(**cv), line 660), so an unknown cv key is a hard TypeError — making the n_splits/embargo doc gap load-relevant, not cosmetic.

**Recommended fix:** Add rows for `conditional_duan`, `feature_selection`, `blend` (+ the `blend` model), `cv.n_splits`, and `cv.embargo` to the doc's tables, mirroring config.py defaults.

### AW-G25 — Doc omits sequences.source enum (and bar_interval/lookback_days) and all daily_lookback sequence features used by real configs

**MEDIUM · context · effort: small · CONFIRMED**

**Location:** `.github/instructions/yaml-config.instructions.md:232` · `workspace/configs/trial_068_gnn_standalone.yaml:96` · `workspace/configs/trial_065_rosenbaum_daily_lstm.yaml:1` · `src/volforecast/config.py:314` · `src/volforecast/config.py:333`

**Evidence:** Doc grep: source:=0, bar_interval=0, lookback_days=0. config.py:314-333 defines source in {parquet, parquet_5min, parquet_5min_multiday, daily_lookback}; 8+ configs set `source: parquet_5min`/`daily_lookback`. Doc sequences.features table (lines 232-244) lists only 9 intraday features, but daily_lookback configs use daily-panel columns: trial_068_gnn_standalone.yaml:96-105 `log_rv_d, log_rv_w, log_rv_m, signed_return_d, abs_ret_d, log_rs_negative_d, log_jump_d, log_bpv_d, log_cont_d`.

**Why it matters:** Configs authored for 5-min or daily-lookback sequence models (trials 065/066/068/071-074) rely on a `sequences.source` field and a feature vocabulary the doc never mentions. An agent editing these against the doc has no valid-values reference for source/bar_interval/lookback_days or the daily feature set, and would treat correct values as unknown. SequenceConfig is **-unpacked (config.py:95,669) so any hallucinated sequences key is a hard TypeError.

**Recommended fix:** Add a `sequences.source` enum table (parquet | parquet_5min | parquet_5min_multiday | daily_lookback) plus bar_interval/lookback_days rows, and a second sequences.features table for daily_lookback panel columns.

### AW-26 — The two always-on files duplicate five rule blocks (~350-1,200 tokens/request) and have already drifted

**MEDIUM · context · effort: small · CONFIRMED**

**Location:** `.github/copilot-instructions.md:15` · `AGENTS.md:217` · `.github/copilot-instructions.md:9` · `AGENTS.md:155` · `.github/copilot-instructions.md:41` · `AGENTS.md:85` · `.github/copilot-instructions.md:72` · `AGENTS.md:23`

**Evidence:** copilot:15 NEVER-run list omits `ruff` that AGENTS:217 adds (drift); file-output (copilot:9 vs AGENTS:155), TDD (copilot:41 vs AGENTS:85), evidence rule, model pinning all stated in full in both. /team depth also drifted (copilot omits AGENTS:25 'max depth 2'). Combined 17,121B injected every request.

**Why it matters:** Both files inject on every Copilot request, so ~350-1,200 duplicated tokens are paid unconditionally and the pair has already diverged (ruff, team depth). Dual-maintenance of HARD rules is how contradictions appear.

**Recommended fix:** Keep copilot-instructions.md the single home of the 9 HARD rules; in AGENTS.md replace lines 23, 85, 155, 217, 145-146 with the existing one-line pointer pattern (AGENTS.md:9).

### AW-27 — Lint-gate contradiction: always-on rule 6 declares lint DISABLED while working-agreements.md/fix.md/execute.md mandate lint after every change

**MEDIUM · broken · effort: trivial · ADJUSTED-CONFIRMED**

**Location:** `.github/copilot-instructions.md:50` · `policy/working-agreements.md:9` · `.github/instructions/python.instructions.md:260` · `workflows/fix.md:277` · `workflows/execute.md:62`

**Evidence:** copilot-instructions.md:50-52 (inside "# Critical Rules (HARD — zero exceptions)"): "## 6. Lint Gate (DISABLED) ... Lint is NOT required after every change." CONTRADICTS working-agreements.md:9 "Run lint, typecheck, and tests after changes"; execute.md:62 "→ lint →"; and fix.md:276 (not :277) "Lint gate is mandatory after every file change (per policy)". working-agreements.md is referenced from python.instructions.md:260 and AGENTS.md:85 (both Test-first-scoped references).

**Why it matters:** For any .py edit the agent holds a HARD 'zero exceptions' file saying lint is off plus referenced agreements saying run it every change; behavior becomes read-order-dependent and a struck-through rule in a HARD list trains the model that HARD rules are negotiable.

**Recommended fix:** Pick one lint policy and propagate. If lint-on-request is intended: rewrite copilot-instructions.md section 6 to "Lint: only on request or pre-commit/PR" (already close), change working-agreements.md:9, and rework the workflow lint gates — fix.md:150-153, 168, 209, 275-276 and execute.md:62,82 — since these deeply enforce mandatory post-change lint. Not a 2-line trivial edit; effort is "small", not "trivial".

### AW-28 — workspace/tmp/ and throwaway-script semantics contradict across the two always-on files (persisted-only vs scripts-mandatory vs ephemeral-delete)

**MEDIUM · broken · effort: trivial · CONFIRMED**

**Location:** `AGENTS.md:154` · `AGENTS.md:206` · `.github/copilot-instructions.md:9` · `.github/prompts/gsvivs-audit.prompt.md:147` · `policy/operating-principles.md:11`

**Evidence:** AGENTS.md:154 'No throwaway scripts in tmp/. Use inline execution. tmp/ is for persisted data only.' vs copilot:9 'ALL file writes (temp files, outputs, scripts, artifacts) MUST go to workspace/tmp/' vs AGENTS.md:206 'Files in workspace/tmp/ are ephemeral … Delete files you create'. gsvivs-audit:147 'Write intermediate scripts to workspace/tmp/'.

**Why it matters:** An agent needing a helper script (gsvivs-audit's whole premise is parsing a 73k-line JSON) has no instruction-compliant path — one file bans scripts in tmp, the other mandates them there, and rule 2 restricts running them. It picks one to violate at random.

**Recommended fix:** Single policy in copilot-instructions.md: 'workspace/tmp/ is the only writable scratch area; prefer inline/one-liners; delete anything created; persisted outputs go to workspace/<area>/.' Delete AGENTS.md:154-155 in favor of the cross-ref.

### AW-29 — Mandated market-data refs are 2x over the ref line cap and use Brazil-desk examples for a US-equity project

**MEDIUM · context · effort: medium · ADJUSTED-CONFIRMED**

**Location:** `memory/ref/python-tsdb.md:21` · `memory/ref/python-chunk.md:24` · `.github/instructions/python.instructions.md:11` · `memory/design.md:49`

**Evidence:** python.instructions.md:11 mandates python-tsdb.md before market-data/Slang work (line 8 "Before writing or modifying Python code that accesses market data"): 514 lines/22,838B≈5,709t (P1, ref cap 250 — linter WARNs "exceeds ref soft cap of 250"). Field dictionary ~184-187 field rows (not 266); all examples Brazilian (_lib_eq1d_brazil_tsdb_fns, DAPQ40, PETR4.SA @ tsdb:21/26/43). python-chunk.md 333 lines/12,016B≈3,004t with America/Sao_Paulo (chunk:24) and WINJ25. Project universe is 34 US symbols + E-mini (research/data-access.md:15). Both are P1, so design.md:49's "P2/P3 no line cap" exemption does not apply.

**Why it matters:** Per market-data task ~8.7k tokens of mandated reading, roughly half noise, and Brazil symbol/timezone conventions actively mislead symbol-naming and tz for this project; both files breach the repo's own ref-cap lint.

**Recommended fix:** Distill both to <=250 lines with eqpad_/US, America/New_York examples; move the TSDB field dictionary to a P2 python-tsdb-fields.md loaded on field lookup only. Est ~4-5k tokens/task.

### AW-G29 — pre-commit mypy runs from repo root where no [tool.mypy] exists, dropping check_untyped_defs and warn_unused_ignores that CI/./vol apply

**MEDIUM · broken · effort: small · CONFIRMED**

**Location:** `.pre-commit-config.yaml:17` · `src/pyproject.toml:72` · `vol:244` · `.github/workflows/ci.yml:37`

**Evidence:** pre-commit mypy: `args: [--ignore-missing-imports]`, `additional_dependencies: [numpy, pandas-stubs]` (config:17-22), run from repo root (no root pyproject with [tool.mypy]). Config lives at src/pyproject.toml:72-76 (`check_untyped_defs = true`, `warn_unused_ignores = true`). ./vol (vol:244) and CI (ci.yml:37) run mypy from cwd=src, so they read it.

**Why it matters:** mypy discovers config from CWD, not from the passed file paths. pre-commit's hook therefore type-checks with defaults (check_untyped_defs=false), in an isolated env with only numpy+pandas-stubs and per-file. A type error inside an untyped def, or an unused ignore, passes pre-commit but fails ./vol typecheck and CI on identical code.

**Recommended fix:** Point the pre-commit mypy hook at the real config and target: add `args: [--config-file=src/pyproject.toml, --ignore-missing-imports]` and scope files to `^src/` (files: '^src/.*\.py$'), and align additional_dependencies with the project's actual imports.

### AW-30 — Task-Based Execution boilerplate copy-pasted into ~33 SKILL.mds (~27KB / 6,700 tokens) duplicating memory/ref/vscode-tasks.md, with live filename drift

**MEDIUM · context · effort: medium · ADJUSTED-CONFIRMED**

**Location:** `skills/SLANG_REVIEW/SKILL.md:163` · `skills/SLANG_LINT/SKILL.md:152` · `skills/GIT/SKILL.md:1` · `memory/ref/vscode-tasks.md:1`

**Evidence:** grep -rl '## Task-Based Execution' skills/ = 34 files (heading form "## Task-Based Execution (Zero Allow — Preferred)"; cited GIT/SKILL.md heading is at line 56, not :1). Section bytes (heading→next ##) sum = 27,036 (~6,759t); max SLANG_REVIEW/SKILL.md = 4,430B. Drift: create_and_run_task in only SLANG_LINT + SLANG_REVIEW (2 files) while 37 use run_task; run_id-vs-fixed contradiction inside GIT/SKILL.md L62 vs L74. Loading is on-demand per AGENTS.md:174 — sections do not stack per-request; the aggregate is a maintainability/drift cost, and a meaningful fraction of the bytes are legitimately skill-specific (args schemas/examples), not vscode-tasks.md duplication.

**Why it matters:** Per skill load ~200 tokens of identical protocol prose, and 33 copies of the run_task contract are why AW-04's args-filename contradiction exists in several skills. One canonical copy fixes both cost and drift.

**Recommended fix:** Replace each section with a 4-line block (task label, args-file path, one example JSON, 'Protocol: memory/ref/vscode-tasks.md'); validate via lint_vscode_md cross-ref.

### AW-G30 — pre-commit ruff/ruff-format run repo-wide from root; files outside src/ get ruff DEFAULT config (line-length 88, E+F only) while CI/./vol only lint src/ with the project ruleset

**MEDIUM · broken · effort: small · CONFIRMED**

**Location:** `.pre-commit-config.yaml:5` · `src/pyproject.toml:65` · `vol:238` · `.github/workflows/ci.yml:31`

**Evidence:** ruff hooks have no files:/exclude: (config:5-7), so pre-commit passes all staged .py from repo root. Config is at src/pyproject.toml:65-70 (`line-length = 100`, select `E,F,W,I,UP`). ./vol `ruff check .` (vol:238) and CI `ruff check .` (ci.yml:31) both run from cwd=src, scoping to src only.

**Why it matters:** ruff discovers config by walking up from each file; for files outside src/ (e.g. workspace/lint/design_lint.py, workspace/scripts/*.py, workspace/presentation/generate.py) there is no [tool.ruff], so pre-commit lints them with defaults (line-length 88, only E+F). Those same files are NEVER linted by CI/./vol. Same code, different/absent verdict per surface.

**Recommended fix:** Either add a root pyproject/ruff.toml (or `extend` from src) so out-of-src Python shares the ruleset, or scope the pre-commit ruff hooks with `files: '^src/.*\.py$'` so all three surfaces cover exactly the same tree.

### AW-31 — Skill-as-knowledge-store: FORWARD_NETWORK tells agents to 'consult' a 485KB (~121k token) OpenAPI spec; CANVAS/TMD are majority inline API tables

**MEDIUM · context · effort: small · ADJUSTED-CONFIRMED**

**Location:** `skills/FORWARD_NETWORK/src/forward_network_api.yaml:1` · `skills/FORWARD_NETWORK/SKILL.md:129` · `skills/CANVAS/SKILL.md:43` · `skills/TMD/SKILL.md:1` · `skills/design.md:73`

**Evidence:** forward_network_api.yaml=485,434B≈121,359t (12.3% of 3,955,654B tracked). SKILL.md:129 "Consult ... for complete schemas" — no grep recipe, no "don't read whole file" guard; skill absent from AGENTS.md used-skills table (line 199: "not used in this project's workflow"). CANVAS/SKILL.md=260 lines (11,265B≈2,816t) trips design_lint WARN≥250 (design.md:49); §"Canvas Backend Endpoints" spans lines 43-~192 with 46 pipe-table rows. TMD/SKILL.md=149 lines (5,643B≈1,411t) — 33 table rows; does NOT trip the 250-line WARN. design.md:73 names "skill as knowledge store" an anti-pattern.

**Why it matters:** A compliant read of the spec detonates ~60% of a 200k window; CANVAS/TMD loads pay ~1.5-2.8k tokens of reference tables when the task needs one endpoint.

**Recommended fix:** FORWARD_NETWORK: replace SKILL.md:129 with a grep/one-liner extraction recipe plus explicit "NEVER read the whole 485KB yaml", or delete the AGENTS.md-declared-unused skill. CANVAS: it trips the ≥250-line WARN — move the endpoint tables to src/endpoints.md and keep a ~10-row "most used" table + pointer. TMD: under the WARN threshold; trimming is polish only, not lint-driven.

### AW-32 — Hardcoded real kerberos IDs, employee PII, and book/trade identifiers in write-capable skill examples, against design.md's own anti-pattern

**MEDIUM · security · effort: medium · CONFIRMED**

**Location:** `skills/ETASK/SKILL.md:108` · `skills/NDS_INFRA/SKILL.md:70` · `skills/DIRGET/SKILL.md:48` · `skills/OUTLOOK/SKILL.md:79` · `skills/SLANG_EDIT/SKILL.md:200` · `skills/SECDB_POSITION/SKILL.md:66` · `skills/TMD/SKILL.md:69`

**Evidence:** ETASK: `--kerberos {kerberos}` (19x) on complete/cancel/archive WRITE ops; NDS_INFRA: {name}, jane.doe@example.gs.com, IP 10.0.0.1, Serial {serial}; DIRGET/OUTLOOK real names+emails; SLANG_EDIT:200 `~{kerberos2}!commit`; SECDB_POSITION:66 `~{kerberos}!clean`; TMD `--kerberos {kerberos}` (7x). design.md:75 bans this; sibling files use {kerberos} placeholders.

**Why it matters:** An agent copying these examples runs write-capable ops (complete a task, commit to a userdb) against another employee's identity/inbox, and identifiable colleague PII (name, email, kerberos, desk, machine IP/serial) is committed in a repo now on a personal machine — doxxing/social-engineering aid.

**Recommended fix:** Replace all real kerberos/names/emails/IPs/serials with placeholders ({kerberos}, jane.doe@example.gs.com, 10.0.0.1) + 'resolve from memory/person/user.md'; add these files to the lint_hardcoded_env scan scope.

### AW-33 — GSSSO ~24h SSO cookie written plaintext to workspace/tmp/, which is not gitignored

**MEDIUM · security · effort: trivial · CONFIRMED**

**Location:** `skills/GSSSO_AUTH/src/get-cookie_task.cmd:36` · `ml-vol-estimator.code-workspace:158` · `.gitignore:31`

**Evidence:** SKILL.md:75 'writes the cookie to workspace/tmp/gssso_cookie.txt automatically'; task args `[--out-file, workspace/tmp/gssso_cookie.txt]`. .gitignore covers only workspace/tmp/.pytest_cache/ — workspace/tmp/ itself is stageable (only GIT_COMMIT's deny-list blocks it).

**Why it matters:** The cookie is a ~24h firm-wide SSO credential valid across many *.gs.com APIs; persisting it cleartext in the working tree (readable by any local process, one careless git add from commit) turns a memory-only secret into an on-disk credential on an unmanaged machine.

**Recommended fix:** Add `/workspace/tmp/` to .gitignore; prefer returning the cookie on stdout / in-memory read, or write to an OS temp dir with 0600 and delete after use.

### AW-34 — _dormant is a load-bearing dependency of 10 skills + 2 active memory files but is excluded from all 4 linters and has no wake mechanism

**MEDIUM · architecture · effort: medium · ADJUSTED-CONFIRMED**

**Location:** `memory/INDEX.md:9` · `memory/slang/best-practices.md:15` · `workspace/lint/lint_broken_refs.py:68` · `workspace/lint/validate_memory.py:217` · `memory/meta/guide.md:83`

**Evidence:** INDEX.md:9 "Dormant files: 37 files in memory/_dormant/ ... Restore if Slang work resumes" is the entire spec; guide.md:82-85 status enum (draft/active/stale/archived) has no 'dormant' value and 36/37 dormant files carry status:active. Yet 10 skills (AI_SLOP_CLEANER, CANVAS, CONFLUENCE, ETASK, GITLAB_PIPELINES, GSSSO_AUTH, OUTLOOK, SLANG_EDIT/GLIMPSE/REVIEW) plus 2 active P1 memory files (slang/best-practices.md:15, slang/lint-edit.md:256) reference _dormant paths in-place as the authoritative content source, while all 4 linters (design_lint.py:588, lint_broken_refs.py:68, lint_memory_index_completeness.py:37, validate_memory.py:217) SKIP _dormant. The blind spot lets malformed YAML frontmatter go undetected (memory/_dormant/sys/secdb.md has a dangling ' - sys/enghub.md' sequence item under scalar 'source:'). NOTE: the original 'committed PAT' claim is unsupported — confluence-auth.md contains only placeholder tokens (<your-token-here>), no real secret.

**Why it matters:** 'Dormant' is fiction: the content is load-bearing yet has no INDEX rows (undiscoverable), no restore procedure, and sits in a lint blind spot where broken links, malformed frontmatter (secdb.md), and the committed PAT go undetected.

**Recommended fix:** Promote the ~8 skill-referenced _dormant files back to active domains with per-file INDEX rows (they are undiscoverable today); document a park/restore procedure and add a 'dormant' (or 'parked') state to guide.md's status lifecycle so the 36 status:active files stop lying; make lint_broken_refs validate _dormant targets that are referenced from active files, and scan _dormant as a source tree so malformed frontmatter like secdb.md is caught. Drop the security framing — there is no committed secret.

### AW-35 — subagent_protocol.md and context-isolation.md are ~80% redundant, the context-packet schema lives in 3 places, and /team depth drifted

**MEDIUM · organization · effort: medium · ADJUSTED-CONFIRMED**

**Location:** `policy/subagent_protocol.md:35` · `policy/context-isolation.md:48` · `workflows/plan.md:80` · `workflows/team.md:217` · `policy/subagent_protocol.md:65`

**Evidence:** Packet schema duplicated in 3 tracked files (subagent_protocol.md:36, context-isolation.md:49, plan.md:79 — grep -c subtask_id: = 1 each). Both policy files (5291B + 5566B) are cited as a pair by copilot-instructions.md:74 ("always include the context packet schema from policy/subagent_protocol.md"), AGENTS.md:34, execute.md:108, INDEX.md:15 — so both load together per subagent workflow (~2.7k tok, per-workflow not per-request). Depth drift is a true contradiction: subagent_protocol.md:65 and context-isolation.md:137 permit /team depth=2 (leader→worker→sub-worker) while team.md:217 says "Workers must NOT spawn sub-workers … unless explicitly authorized." Overlap is only ~40%, not 80%: subagent_protocol.md uniquely holds Model Pinning, Roles, Concurrency, Failure Handling, and a ~2KB Terminal Isolation HARD-RULE block (lines 81-90); context-isolation.md uniquely holds Philosophy, Orchestrator Behavior, Anti-Patterns, Workflow Integration. 
 Keep the canonical packet schema, return contract, spawn-threshold table and depth table in ONE file (subagent_protocol.md); replace the copies in context-isolation.md:48-93/132-138 and plan.md:78-88 with a one-line pointer. Preserve each file's unique sections (Terminal Isolation, Anti-Patterns, etc.) — do NOT collapse to a single ~1.4k file. Resolve the /team depth contradiction to one value across subagent_protocol.md:65, context-isolation.md:137, and team.md:217. Realistic token saving is ~700 (the 4 duplicated sections), not half.

**Why it matters:** Per subagent workflow the model reads ~2.7k tokens where ~1.4k would do; drift already happened (team.md forbids what policy permits), and a schema change must be made in 3 places or downstream verifiers reject packets.

**Recommended fix:** Merge into one file; keep the packet schema and depth table only in subagent_protocol.md and replace copies in plan.md/context-isolation.md with a one-line reference; resolve team depth to a single value.

### AW-36 — KILL_ORPHANS maintains two divergent process-killer implementations wired to different entry points, and pastes its Troubleshooting section 3x

**MEDIUM · architecture · effort: small · CONFIRMED**

**Location:** `skills/KILL_ORPHANS/SKILL.md:21` · `skills/KILL_ORPHANS/src/cleanup.py:1` · `skills/KILL_ORPHANS/src/cleanup.ps1:1` · `.github/prompts/kill-orphans.prompt.md:15` · `skills/KILL_ORPHANS/SKILL.md:78`

**Evidence:** SKILL.md:21 Tool=cleanup.py (15,892B); the task wrapper uses cleanup.py; but kill-orphans.prompt.md:15 runs `& cleanup.ps1 -DryRun` (9,163B, raw PowerShell). SKILL.md lines 78-96: identical Troubleshooting table repeated 3x. Also relies on wmic (removed in Win11 24H2+).

**Why it matters:** Two independent kill-heuristic engines for a DESTRUCTIVE op must be kept identical by hand — a guard added to cleanup.py but not .ps1 silently kills wanted processes via the slash prompt; the prompt path also runs raw terminal PowerShell, bypassing the no-run_in_terminal doctrine.

**Recommended fix:** Pick cleanup.py, route SKILL.md and the prompt through run_task('kill-orphans') with --dry-run, delete cleanup.ps1; delete two of the three Troubleshooting copies; switch parent-map query to Get-CimInstance/psutil.

### AW-37 — 'fix it.prompt.md' filename contains a space with no name: override and /housekeep has no prompt file — flagship entry points are unreachable

**MEDIUM · broken · effort: trivial · ADJUSTED-CONFIRMED**

**Location:** `.github/prompts/fix it.prompt.md:1` · `workflows/fix.md:10` · `workflows/housekeep.md:11`

**Evidence:** .github/prompts/fix it.prompt.md:1-5 frontmatter = description/argument-hint/model only, no `name:` (grep -c ^name: = 0); filename contains a space. workflows/fix.md:10 documents trigger `- User explicitly uses `/fix it``; fix.md is 16228 bytes. `/fix` is a Copilot built-in, so `/fix it` resolves to built-in /fix + arg 'it' or collides. workflows/housekeep.md:10 (NOT :11): `- User explicitly uses `/lint-workspace` or `/housekeep``. No housekeep.prompt.md exists, so the literal `/housekeep` command is a dangling reference — but lint-workspace.prompt.md:11 references `workflows/housekeep.md`, so the housekeep workflow IS reachable via /lint-workspace (INDEX.md:30: 'Maintenance (via /lint-workspace)'). HYPOTHESIS remains on exact VS Code resolution of a spaced prompt basename.

**Why it matters:** Typing '/fix it' resolves to built-in /fix with arg 'it', so the 16KB fix.md pipeline is likely never invocable by its intended trigger; /housekeep can never fire. Confirm by running /fix it and inspecting the resolved command.

**Recommended fix:** git mv '.github/prompts/fix it.prompt.md' to fix-it.prompt.md (or add `name: fix-it`) AND reconcile fix.md:10's documented `/fix it` trigger to the collision-free command, noting the /fix built-in clash. For housekeep: either add housekeep.prompt.md or drop `/housekeep` from housekeep.md:10 (leave /lint-workspace, which already works).

### AW-38 — plan.md forbids the exact yield-back that execute.md prescribes — the default plan->execute chain dead-ends on unclear scope

**MEDIUM · broken · effort: trivial · ADJUSTED-CONFIRMED**

**Location:** `workflows/plan.md:159` · `workflows/execute.md:76`

**Evidence:** plan.md:159 'Max composition depth: `plan → execute → plan` is not allowed. If `execute.md` needs re-scoping, it must escalate to the user.' contradicts execute.md:76 '| Scope unclear mid-execution | → Yield to `plan.md`, resume on return |' AND execute.md:104 '- Max 1 yield to `plan.md`. No circular yields.' The default chain is confirmed (plan.md:145 '| Default | plan → execute |'; execute.md:11 '`plan.md` yields here after producing a plan'), so execute's own transition table and constraints both prescribe the exact yield its parent declares illegal.

**Why it matters:** plan is the default route, so the most common chain hits this contradiction the first time scope blurs: execute's transition table sends it somewhere its parent declares illegal, and a yield violates the plan contract silently.

**Recommended fix:** Make both execute.md lines entry-source aware. Line 76: 'Scope unclear mid-execution | → if entered from plan.md, escalate to user; else yield to plan.md (max 1)'. Line 104: change 'Max 1 yield to plan.md' to 'Max 1 yield to plan.md only when NOT entered from plan.md; otherwise escalate to user' — matching plan.md:159. Fixing only :76 leaves :104 contradicting plan.md.

### AW-40 — Personal-tutoring machinery occupies 6 of 34 slash commands and 490KB of tracked state in a work repo

**MEDIUM · optimization · effort: medium · CONFIRMED**

**Location:** `.github/prompts/study.prompt.md:2` · `.github/prompts/teach.prompt.md:1` · `.github/prompts/quiz.prompt.md:1` · `.github/prompts/expand-learning-graph.prompt.md:1` · `.github/prompts/weekly-learning-goals.prompt.md:1` · `.github/prompts/learning-status.prompt.md:1`

**Evidence:** 6 tutoring prompts = 3,704B; loose skills study/teach/quiz/learning-status/expand-learning-graph/weekly-learning-goals = 32,402B; git ls-files workspace/learning = 490,563B (incl. dashboard.html + 68KB design doc). /study already auto-routes /teach and /quiz.

**Why it matters:** Six picker entries for one activity crowd the / dropdown next to work commands (/learn, unrelated memory distillation, sits inside the cluster — mis-invocation risk); /teach and /quiz are redundant with /study; 490KB of mastery state + generated dashboard.html are personal data in the team-visible tree.

**Recommended fix:** Collapse to /study + one /learning (status|goals|expand); or relocate all 6 to VS Code user-profile prompts. Gitignore workspace/learning/dashboard.html.

### AW-41 — _run wrappers always exit 0, so bootstrap/lint failures and timeouts are invisible — the agent polls an out_file that never appears

**MEDIUM · architecture · effort: small · ADJUSTED-CONFIRMED**

**Location:** `skills/_shared/_run.cmd:57` · `skills/_shared/_run.sh:89` · `workspace/lint/lint_all.py:172` · `vol:346`

**Evidence:** _run.cmd unconditional 'exit /b 0' is at line 59 (line 57 is the comment); _EC captured @55, ignored. _run.sh 'exit 0' at line 90 (comment @89). workspace/lint/lint_task.cmd:3 calls _run.cmd with lint_all.py. lint_all.py:172 'subprocess.run(args, capture_output=True, timeout=120)' has no try/except; TimeoutExpired re-raises at future.result() (line 280), bypassing _flush_out (line 305). vol:346 runs the command, vol:347 'echo "EXIT_CODE=$?"' returns 0 so wait/_EXIT/exit are all 0. Correction: the missing-venv/H: bootstrap path exits /b 1 (not 0) at _run.cmd:36, so that specific 'silent' example is inaccurate; the truly masked cases are a post-bootstrap Python crash and the >120s lint hang. Consumer model per memory/ref/vscode-tasks.md E7/E100 is run_task-blocks-then-read_file, not polling (polling is the vol bg path at vol:360+).

**Why it matters:** Success/failure is communicated solely via out_file content; a crash/hang before the file write (missing H: drive, >120s lint, failed command) leaves the terminal auto-closed with no diagnostic, and `./vol exec pytest` returns success on failure — the exact 'fail silently' class the rules warn about.

**Recommended fix:** On bootstrap/lint failure write {status:done,gate:FAIL,error} to output_json before exiting; wrap lint_all subprocess in try/except TimeoutExpired and main() in try/finally; in vol capture rc first (`rc=$?; echo EXIT_CODE=$rc; exit $rc`) and guard wait under set -e.

### AW-42 — Boot sequence specified twice with drift: AGENTS.md Boot Protocol vs workflows/bootup.md read different file sets

**MEDIUM · organization · effort: trivial · ADJUSTED-CONFIRMED**

**Location:** `AGENTS.md:54` · `workflows/bootup.md:17` · `workflows/bootup.md:52`

**Evidence:** AGENTS.md:54 "**Session start (always):**" lists 4 reads (55-58); bootup.md:15-21 lists 5 reads omitting memory/INDEX.md; bootup.md:52 "No P1/P2 memory at boot." Overlap is user.md(3437B)+project-state.md(10038B)=13475B; session-handoff.md is conditional and does not currently exist. Extra: AGENTS.md self-contradicts — step 3 (line 57) reads INDEX.md "always" while line 60 says only the 2 P0 files are "Always" and "Everything else loads on demand."

**Why it matters:** A /bootup session never loads memory/INDEX.md, so the on-demand lookup tables AGENTS.md:133 depends on are unavailable that session; always-on boots never load the trial registry the experiment loop needs; two lists drift independently, re-reading ~13.5KB of overlapping files.

**Recommended fix:** Fix is valid: make bootup.md step 1 "Execute the AGENTS.md Boot Protocol; do NOT re-read" and keep only its delta (trials.yaml slice, latest journal entry, scorecard synthesis/output format). Additionally reconcile AGENTS.md's own INDEX.md ambiguity (step 3 vs line 60) so the single canonical boot list is unambiguous. Frame the defect as spec drift/contradiction between two non-cross-referencing checklists, not guaranteed file-skipping or token doubling.

### AW-43 — No prompt INDEX and no runnable onboarding path: .github/prompts/ is the only artifact layer without a registry, and AGENTS.md lacks a first-run sequence, src/ map, and copilot-setup-steps.yml

**MEDIUM · organization · effort: medium · CONFIRMED**

**Location:** `AGENTS.md:62` · `AGENTS.md:160` · `AGENTS.md:214` · `vol:20` · `.gitignore:28`

**Evidence:** skills/workflows/personas/memory each have INDEX.md; .github/prompts/ (34 files) has none. AGENTS.md Workspace table (160-168) omits src/ (307 tracked files); env setup is 3 lines ('Install via nix-env -iA nixpkgs.uv'); no copilot-setup-steps.yml exists; no data ingest prerequisite (src/data/ gitignored).

**Why it matters:** A contributor/model can't enumerate commands or resolve overlaps (lint vs lint-workspace, debug vs 'fix it') without opening 34 files; a fresh Copilot coding agent can't locate the code it must edit, has no `./vol sync` step, and every ./vol call dies at vol:20 'uv not found' because uv is absent on GitHub-hosted Ubuntu with no nix.

**Recommended fix:** Add .github/prompts/INDEX.md linked from AGENTS.md:62; add a 'First run' block (src/ row, `pipx install uv → ./vol sync → ./vol test-all`, data note) and a .github/workflows/copilot-setup-steps.yml installing uv + syncing.

### AW-44 — pre-commit pins ruff v0.4.4 / mypy v1.10.0 while the project locks ruff 0.15.12 / mypy 2.0.0, and no doc tells agents pre-commit exists

**MEDIUM · quality · effort: trivial · ADJUSTED-CONFIRMED**

**Location:** `.pre-commit-config.yaml:3` · `.pre-commit-config.yaml:18` · `src/uv.lock:1`

**Evidence:** .pre-commit-config.yaml:3 `rev: v0.4.4` (ruff), :18 `rev: v1.10.0` (mirrors-mypy) vs src/uv.lock:2856 ruff `version = "0.15.12"` and src/uv.lock:1740-1741 mypy `version = "2.0.0"`. No agent-facing doc references pre-commit: grep of AGENTS.md and .github/** finds pre-commit only in Slang `@ScriptVal::PreCommit` (unrelated) and workspace/design.md:163 (non-injected design doc, refers to structure validator not ruff/mypy). copilot-instructions.md:15/22 and AGENTS.md:217 tell agents to use `./vol` and never run ruff/mypy directly.

**Why it matters:** Ten+ minor versions of ruff drift means pre-commit ruff-format and ./vol fmt disagree, producing hook fights; mypy 1.10 vs 2.0 flags different errors than CI; and nothing in AGENTS.md/copilot-instructions tells agents the hooks mutate staged files.

**Recommended fix:** Fix uv.lock citation to src/uv.lock:2856 (ruff) and :1740 (mypy). Bump ruff-pre-commit rev to v0.15.12 and mirrors-mypy to match the locked mypy (verify an upstream tag exists — the locked mypy 2.0.0 may not map to a real mirrors-mypy tag; if not, pin to the newest available and reconcile). Add one line to copilot-instructions rule 8 / AGENTS env noting pre-commit hooks (ruff --fix, ruff-format, mypy) mutate staged files on commit and use a separate env from ./vol. Alternatively, if the config is vestigial (nothing invokes it; ./vol is the mandated path), delete .pre-commit-config.yaml to remove the drift entirely.

### AW-45 — GIT skill's flagship 'Full push workflow' example uses git add -A, violating its own rule that protects the embedded repo

**MEDIUM · quality · effort: trivial · ADJUSTED-CONFIRMED**

**Location:** `skills/GIT/SKILL.md:112` · `skills/GIT/SKILL.md:137` · `skills/GIT_COMMIT/SKILL.md:186` · `skills/GIT_COMMIT/src/commit_task.py:23`

**Evidence:** SKILL.md:112 (Full push workflow) `["add","-A"]` — plus a SECOND identical example at SKILL.md:40 — both violate SKILL.md:137 "NEVER git add -A (embedded repo at workspace/docs/enghub/)". Rationale path is stale: ENGHUB now clones to workspace/knowledge/enghub/ (skills/ENGHUB/src/enghub.py:26, clone-all.sh:7), yet GIT/SKILL.md:137 and GIT_COMMIT/src/commit_task.py:23 still cite workspace/docs/enghub/. Note: root .gitignore:30 (`workspace/knowledge/enghub/`) fully ignores the current clone path, so add -A would not in fact stage the embedded repo — the concrete "stages the embedded repo" harm is mitigated; the live defect is the self-contradicting example (agents copy the most complete one) plus a deny-list that guards a path the tool no longer uses.

**Why it matters:** Agents copy the most complete example, not the prose rule 25 lines later; following it stages the embedded repo — the exact failure the rule prevents — and the convention is maintained in two skills plus memory/ref/git-workflow.md (drift surfaces).

**Recommended fix:** Fix both add -A examples (SKILL.md:40 and :112) to explicit file staging. Update commit_task.py DENIED_PREFIXES to include workspace/knowledge/enghub/ (keep or replace the old path). Optionally centralize the Conventions block in memory/ref/git-workflow.md (both skills already link it at GIT/SKILL.md:136/173 and GIT_COMMIT/SKILL.md:184/192).

### AW-46 — 'powershell'-fenced examples use cmd-only ^ line continuation in 5 SLANG SKILL.md files

**MEDIUM · broken · effort: small · CONFIRMED**

**Location:** `skills/SLANG_GLIMPSE/SKILL.md:47` · `skills/SLANG_LINT/SKILL.md:38` · `skills/SLANG_REGTEST_FIX/SKILL.md:59` · `skills/SLANG_REVIEW/SKILL.md:44` · `skills/SLANG_REVIEW_INSPECT/SKILL.md:37`

**Evidence:** ```powershell fences with `PYTHON ... lint.py ^` continuation — ^ is cmd.exe continuation; PowerShell uses backtick.

**Why it matters:** An agent copying these multi-line commands into a PowerShell terminal (as the fence says) runs the tool with a literal '^' arg and no --db, then executes '--db ...' as a separate broken statement — every terminal-mode fallback example in these five skills fails as written.

**Recommended fix:** Fence as ```cmd (or wrap in cmd /c), or replace ^ with backtick continuations / single-line commands.

### AW-47 — Keyword-dispatch registry routes only to de-scoped GS-internal skills; zero project skills registered, and dispatch keywords collide

**MEDIUM · architecture · effort: small · ADJUSTED-CONFIRMED**

**Location:** `workflows/INDEX.md:23` · `workflows/INDEX.md:45` · `AGENTS.md:199` · `skills/design.md:52`

**Evidence:** 48 skill dirs exist (git ls-files skills/*/SKILL.md = 48; skills/INDEX.md registry = 48). Dispatch table (workflows/INDEX.md:47-57) has 11 rows; 10 name real skills, PROCMON names none (PROCMON_LOGS:62, PROCMON_JOBS:63 exist). So ~38 of 48 skills lack the workflows/INDEX.md entry required by skills/design.md:52 rule 9 — not "43 of 54". "10 of 11 K-P skills" is garbled; accurate: 10 of 11 dispatch rows resolve to a skill, PROCMON does not. design_lint.py checks 1-26 include no skill→workflows/INDEX.md registration check, confirming §4.9 (design.md:96 Gaps) is unlinted.

**Why it matters:** Promptless requests ('train the model','run a backtest') can never keyword-route to project skills; the routing layer serves only unused skills, ~43 of 54 skills violate the registration rule (design.md §4.9 admits it's unlinted), and ambiguous keywords make plan vs interview nondeterministic.

**Recommended fix:** Add dispatch rows for the 9 project skills (AGENTS.md:180-188) or explicitly document that project skills route via /prompt+workflows and are exempt from §4.9's workflows/INDEX.md requirement; replace the PROCMON row with PROCMON_JOBS/PROCMON_LOGS; remove "don't assume"/"let's discuss" from the Plan row (INDEX.md:23) to disambiguate from Interview (INDEX.md:36); implement the §4.9 skill-registration check in design_lint.py.

### AW-48 — memory/research/README.md is an orphaned stale second index that /research actively loads; INDEX.md lacks status/date columns so it routes to archived files

**MEDIUM · broken · effort: small · ADJUSTED-CONFIRMED**

**Location:** `memory/research/README.md:13` · `memory/research/README.md:44` · `.github/prompts/research.prompt.md:13` · `memory/INDEX.md:60` · `memory/research/layer01-gap-analysis.md:5`

**Evidence:** memory/research/README.md (3230B≈808 tokens, git-tracked) lists project-plan.md/open-questions.md/project-proposals.md — none exist in memory/research/ (git ls-files confirms only README tracked among them). README is absent from INDEX.md (grep→no match), violating design.md §4 rule1 and Anti-Pattern 3 (orphan). research.prompt.md:13 loads it on every /research invocation. INDEX.md:60 routes load-trigger 'Layer 0-1 implementation, feature gaps' to layer01-gap-analysis.md (frontmatter status:archived line5; banner line13 'All 9 gaps below are now implemented'); the archived doc is 12295B≈3074 tokens (INDEX's ~2250 is an undercount). INDEX columns lack any Status/Updated field.

**Why it matters:** /research injects a stale tier map with 3 dead filenames every session; INDEX has no Status column so it directs agents into archived docs, wasting ~3k tokens and risking stale conclusions.

**Recommended fix:** Delete README.md and point research.prompt.md:13 at INDEX's research section; add Status/Updated columns to INDEX populated from frontmatter and drop archived files from Load Trigger routing.

## Severity: Low (18 findings) — polish

### AW-G4 — Rule 9 forbids every currently-available Anthropic model (Sonnet, Haiku) and never names Claude Fable 5, the actual current flagship — leaving no sanctioned compliant model if Opus 4.6 is unavailable

**LOW · quality · effort: trivial · ADJUSTED-CONFIRMED**

**Location:** `.github/copilot-instructions.md:72`

**Evidence:** copilot-instructions.md:72 pins "Claude Opus 4.6" and bans Sonnet/Haiku/GPT; Fable 5 absent from entire tracked tree (grep -i fable = 0 hits). However "Opus 4.6" is hard-coded as a working, selectable value across 35+ tracked files: AGENTS.md:23, 34 prompt frontmatters (model: Claude Opus 4.6), and skills/*.md. Nothing in the repo shows Opus 4.6 is unavailable, so the claimed empty allow-set / agent-paralysis does not reproduce from repo evidence — it relies on external model-availability assumptions. The verifiable issue is a maintainability/staleness smell (a single model literal duplicated 35+ times with no capability-based fallback), not a present functional defect.

**Why it matters:** If 'Opus 4.6' is not selectable, the rule's allow-set is empty among available Anthropic models: it explicitly forbids the two that exist (Sonnet/Haiku) and never whitelists Fable 5 (the flagship this very audit runs on). The agent is left with an instruction it cannot satisfy, forcing either silent violation or paralysis.

**Recommended fix:** Add a capability-based fallback clause to the prose rules (rule 9 in copilot-instructions.md and AGENTS.md:23), e.g. "use the strongest available Anthropic model; do not downgrade to small/short-context models." Note the frontmatter model: fields in the 34 prompt files require a concrete valid model ID, so a literal must be retained and version-bumped there — capability phrasing alone cannot replace those. Treat this as a low-priority consistency cleanup, not a blocker.

### AW-G5 — Two divergent identifier forms for the same pin — display name 'Claude Opus 4.6' vs slug 'claude-opus-4-6' — signals uncertainty about what VS Code actually matches

**LOW · organization · effort: trivial · ADJUSTED-CONFIRMED**

**Location:** `.github/prompts/execute.prompt.md:4` · `workspace/learning/vol-learning-framework-design.md:1079` · `workspace/learning/vol-learning-framework-design.md:1175`

**Evidence:** Every operative model pin uses the display name: `grep -rl "^model: Claude Opus 4.6" .github/prompts/` = 34 files, all identical form. The API-style slug `claude-opus-4-6` appears in NO consumed file — `grep -rn "claude-opus-4-6" .github/ AGENTS.md skills/ memory/` returns no matches (exit 1). It occurs only twice in workspace/learning/vol-learning-framework-design.md, a design doc cataloged as a P2 on-demand reference in memory/INDEX.md:114 (not injected per request). Line 1079 uses the slug as a parenthetical gloss "Opus 4.6 (claude-opus-4-6)"; line 1175 is a deliberately permissive validation criterion accepting either form. Neither is an operative pin, and the 34 consistent pins show the author did know which form VS Code resolves.

**Why it matters:** VS Code prompt `model:` matches the picker display name, not an API slug, so the two forms are not interchangeable. Carrying both invites a future editor to paste the wrong one and silently break the pin. It also reveals the author was unsure which identifier the platform consumes.

**Recommended fix:** No operative change needed — the 34 prompt pins are already consistent on the VS Code display name. Optional polish: in vol-learning-framework-design.md, drop the bare slug or explicitly label "(claude-opus-4-6 = API slug, informational; VS Code frontmatter uses the display name 'Claude Opus 4.6')" so a future reader does not treat the slug as frontmatter-ready.

### AW-G7 — `forecast` is a registered, working CLI subcommand but has no ./vol case arm — unreachable through the mandated wrapper

**LOW · organization · effort: trivial · ADJUSTED-CONFIRMED**

**Location:** `src/volforecast/__main__.py:213` · `src/volforecast/cli/forecast.py:481` · `vol:412`

**Evidence:** __main__.py:213-215 imports/calls _reg_forecast; forecast.py:480-483 `add_parser("forecast", help=...)` with --symbol/--horizon/--threshold (working parser). `grep -c 'forecast)' vol = 0`, so `./vol forecast` falls to the vol:412 `*)` arm → vol:413 "ERROR: Unknown command". However forecast IS reachable via the sanctioned wrapper paths `./vol exec python -m volforecast forecast` / `./vol bg python -m volforecast forecast` — vol:342-347 and 375-381 activate .venv and export LD_LIBRARY_PATH/TMP/LOCATION, and copilot-instructions.md:23-24 + vol help:202 explicitly sanction exec/bg for arbitrary python. So this is a missing convenience shortcut + help-doc omission (forecast absent from vol help), not an unreachable capability.

**Why it matters:** copilot-instructions.md:15 forbids running python directly ("NEVER run python...they will fail silently"). So `python -m volforecast forecast` is off-limits and `./vol forecast` errors out — the registered forecast capability is unreachable via the only sanctioned interface. Inverse of AW-05: the target exists, the wrapper path is missing.

**Recommended fix:** Either (a) add a `forecast)` arm dispatching `python -m volforecast forecast "$@"` and list it in `./vol help` for parity with the 19 other registered subcommands, or (b) if forecast is meant to be internal, drop the parser registration at __main__.py:213-215. Interim: agents can already run it via `./vol exec python -m volforecast forecast --symbol SPY`. Since the capability is reachable and env-correct today, this is discoverability/consistency polish, not a functional repair.

### AW-G8 — `vol notebook` routes to external jupyter (self-admittedly usually absent) while the sibling cli/notebook.py is an abandoned NotImplementedError stub; two more orphaned stub modules exist

**LOW · quality · effort: small · ADJUSTED-CONFIRMED**

**Location:** `vol:257` · `src/volforecast/cli/notebook.py:30` · `src/volforecast/cli/research.py:30` · `src/volforecast/cli/build_features.py:59`

**Evidence:** vol:257-264 dispatches `jupyter notebook` with a loud missing-jupyter guard (exit 1). cli/notebook.py (30,35) and cli/research.py (30,39,44) raise NotImplementedError and are referenced NOWHERE in the tracked tree. cli/build_features.py (59,64) also stubs NotImplementedError but IS imported by src/tests/unit/test_features.py:20 (`from volforecast.cli.build_features import build_layer`), which tolerates the stub via `pytest.raises((ValueError, NotImplementedError))` at L133-134. None of the three are registered in __main__.py or wired into `vol`.

**Why it matters:** `vol notebook` is a degraded arm — likely to fail on the target box, though it fails loudly with guidance rather than silently. The three NotImplementedError modules are dead code that suggests an intended-but-abandoned CLI surface; a future edit wiring cli/notebook.py into vol would turn the loud failure into an AW-05-style stub dead-end.

**Recommended fix:** Safe to delete cli/notebook.py and cli/research.py (zero references). Do NOT blindly delete cli/build_features.py — its build_layer is imported at test_features.py:20; either finish build_layer, or remove the module together with that import/test block, otherwise pytest collection of test_features.py breaks. Keep the existing explicit jupyter-missing guard in `vol notebook` (vol:258-262) so it never silently no-ops.

### AW-G13 — AGENTS.md hardwires the environment to 'Linux / Coder Workspace' with nix + H: + /sw/ficc assumptions and no branch for a GitHub-hosted runner

**LOW · context · effort: small · ADJUSTED-CONFIRMED**

**Location:** `AGENTS.md:212` · `AGENTS.md:215` · `AGENTS.md:216` · `vol:66`

**Evidence:** AGENTS.md:212 `## Environment (Linux / Coder Workspace)`; :215 `Python: UV-managed, Python 3.11 via nix. Install via nix-env -iA nixpkgs.uv if missing.`; :216 `Tools are on PATH via nix. No env scripts needed.` This is AGENTS.md's ONLY environment section and is Coder-only. Note: H: is NOT in AGENTS.md — it appears as a Windows branch in .github/instructions/python.instructions.md:30 (`cmd /c "H:\uv-env.cmd ..."`) and devtools.md:23; /sw/ficc appears only in vol:66 as an already-handled skip. No copilot-setup-steps.yml exists (.github/workflows/ has only ci.yml), so a GitHub-hosted coding-agent runner is not a provisioned consumer.

**Why it matters:** AGENTS.md is always-injected for the coding agent, so its sole environment description tells the agent it is on a GS Coder box with nix and mapped drives. On the actual GitHub-hosted Ubuntu runner none of that holds, and there is no conditional guidance. The agent will confidently issue nix-env / H: / /sw/ficc-dependent steps that silently fail. This is the root env-assumption break behind the operability findings.

**Recommended fix:** Kernel: AGENTS.md's Environment section assumes the GS Coder box (nix) and has no branch for a GitHub-hosted coding-agent runner. Since devtools.md:23 already documents the Linux-vs-Windows split, have AGENTS.md cross-reference it rather than duplicate, and add one line noting the coding-agent runner needs provisioning. If the Copilot coding agent is actually intended, the real gap is the MISSING .github/workflows/copilot-setup-steps.yml (referenced by the fix but nonexistent) — create it to install uv/python, since nix/H: are absent on a bare Ubuntu runner.

### AW-G17 — workspace/scripts/ holds 15 git-tracked one-off analysis scripts with ~0 agentic references, contradicting AGENTS.md's throwaway-script policy (AW-28)

**LOW · organization · effort: small · ADJUSTED-CONFIRMED**

**Location:** `workspace/scripts/` · `AGENTS.md:154` · `workspace/research/trials.yaml:1144`

**Evidence:** trials.yaml:1144 (trial-042) sets `script: workspace/scripts/gsvivs_threshold_sweep.py`, a file that does not exist (on-disk: sweep_gsvivs_threshold.py, gsvivs_walkforward_threshold.py, sweep_gsvivs_long_flat_threshold.py). trials.yaml is loaded on-demand by .github/prompts/experiment.prompt.md and status.prompt.md, so the dangling path can surface there. The 15 scripts are NOT throwaway/policy violations: AGENTS.md:154 bans throwaway scripts in `tmp/` only, while AGENTS.md:168 designates `workspace/` as "Build here"; workspace/docs/gsvivs_audit_results.md:165 documents these as ordered idempotent pipeline scripts and workspace/plans/plan-b-enriched-5min-lstm.md:163/436 lists build_5min_sequences.py as a deliverable.

**Why it matters:** These are exactly the throwaway/one-off scripts the policy bans, but the policy only scopes `tmp/`, so a whole committed `workspace/scripts/` dir escapes it as session debris in a work repo. AI_SLOP_CLEANER skill (AGENTS.md:197) exists to clean slop yet nothing routes to workspace/scripts/. The lone config reference is itself a dangling wrong path.

**Recommended fix:** Fix trials.yaml:1144 to a real filename (likely sweep_gsvivs_threshold.py) or drop the `script:` field. Do NOT delete workspace/scripts/: it lives in the AGENTS.md-sanctioned "Build here" tree, is referenced by workspace/docs/ and workspace/plans/, and deleting it would break those references and remove a documented idempotent pipeline.

### AW-G18 — data-audit.md's only validation provenance points at a deleted ephemeral tmp/ probe script

**LOW · context · effort: trivial · CONFIRMED**

**Location:** `workspace/docs/data-audit.md:5` · `workspace/docs/data-audit.md:3` · `AGENTS.md:207`

**Evidence:** data-audit.md:5 "**Last validated:** 2026-05-18 (probe script: `workspace/tmp/sp500_data_probe.py`, 147/206 checks passed...". `ls workspace/tmp/sp500_data_probe.py` -> No such file (untracked, absent). AGENTS.md:206-207: "Files in `workspace/tmp/` are ephemeral ... Delete files you create in `workspace/tmp/`."

**Why it matters:** The doc bills itself 'Single source of truth' (line 3) but its sole reproducibility anchor is a throwaway tmp/ file the cleanup policy guarantees is gone, so the '147/206 checks passed' figure is unverifiable and undated relative to current src. An agent trusting the '2026-05-18 validated' stamp cannot re-run it.

**Recommended fix:** Move the probe into workspace/scripts/ or tests/, or replace line 5 with a reproducible command; drop the pass-count if it can't be regenerated.

### AW-G20 — `vol present`/workspace/presentation is live CLI infra invisible to both P1 docs, while workspace/plans is a fully orphan tracked tree

**LOW · context · effort: small · ADJUSTED-CONFIRMED**

**Location:** `vol:181` · `vol:324` · `workspace/docs/user-manual.md:198` · `memory/ref/vol-cli.md:11` · `workspace/plans/`

**Evidence:** vol:324-325 present)→workspace/presentation/generate.py; vol:181 default output; kvar/cache-status/cache-clear at vol:312/318/321. vol-cli.md (3755B subcommand table): 0 occurrences of present/kvar/cache-status/cache-clear. user-manual.md present matches at L49 & L565 only (verb "presents"); cited L198 has no match. CONTRA the plans claim: workflows/plan.md:60 "Plan to workspace/plans/" (the /plan output dir) and personas/model-builder.md:14 "workspace/plans/ files are read-only"; src/volforecast/reporting/html_report.py:3,34 also cite workspace/plans/. Only the 7 individual filenames are unreferenced (expected for per-task plan outputs), not the tree.

**Why it matters:** The doc surface and the repo tree have drifted apart in both directions: a real subcommand (`present`, plus `kvar`/`cache-*`) wired to workspace/presentation is undiscoverable from the P1 files the agent actually loads, while workspace/plans/ holds 7 tracked planning docs that no prompt/skill/instruction/CLI references — orphan debris the /plan workflow does not consume.

**Recommended fix:** Add present/kvar/cache-status/cache-clear rows to memory/ref/vol-cli.md (and present to user-manual.md). Drop the workspace/plans recommendation entirely: it is the documented /plan output directory (workflows/plan.md:60, personas/model-builder.md:14), not orphan debris — do not propose removing it.

### AW-G26 — Doc states ale_features default `top_10` but code default is `top_20` (contradicts its own example)

**LOW · context · effort: trivial · CONFIRMED**

**Location:** `.github/instructions/yaml-config.instructions.md:176` · `src/volforecast/config.py:237` · `src/volforecast/config.py:68` · `.github/instructions/yaml-config.instructions.md:163`

**Evidence:** Doc table row: "| `ale_features` | str or list | `\"top_10\"` |" (line 176). Code: config.py:237 `ale_features: str | list[str] = "top_20"` and parser config.py:68 `raw.get("ale_features", "top_20")`. The doc's own example at line 163 uses `ale_features: top_20`.

**Why it matters:** A minor but concrete factual error in the schema reference: an agent trusting the documented default would assume top-10 ALE features are computed when the code actually defaults to top-20, and the doc even contradicts itself two tables up. Erodes trust in the enum tables that are the point of this instruction file.

**Recommended fix:** Change the default in the line-176 table from `"top_10"` to `"top_20"` to match config.py:237.

### AW-G31 — addopts `--ignore=tests/slow` silently drops the whole tests/slow/ directory from every surface, contradicting ./vol test-all's 'complete/full suite' docs

**LOW · quality · effort: small · ADJUSTED-CONFIRMED**

**Location:** `src/pyproject.toml:84` · `vol:99` · `vol:224` · `.github/workflows/ci.yml:40`

**Evidence:** addopts = "--import-mode=importlib --ignore=tests/slow" (src/pyproject.toml:84) globally excludes the tests/slow/ DIRECTORY from ./vol test, ./vol test-all (vol:224 `pytest tests/`), and CI (ci.yml:40, working-directory: src). Separately, the `slow` MARKER is filtered only by ./vol test via -m "not slow" (vol:218). These are two distinct mechanisms sharing the word "slow". The docs at pyproject.toml:88 ("included in ./vol test-all") and the "complete/full suite" language (vol:99, pyproject.toml:82-83) are TRUE for @pytest.mark.slow tests — grep finds 13 such files in tests/unit/ and tests/integration/ that DO run under test-all. The tests/slow/ directory, however, currently holds NO test files (git ls-files: only __init__.py + conftest.py), and its own conftest.py already documents the design: "excluded from the default pytest run (--ignore=tests/slow) ... Run explicitly with: uv run pytest tests/slow/". So there is a naming-collision / latent trap (any real-data test later added to tests/slow/ would silently never run in any automated surface), but no active dropped tests today and no clean doc "contradiction" — the marker claim is accurate.

**Why it matters:** The tests/slow/ directory runs in NO automated surface — not ./vol test, not ./vol test-all, not CI — because the ignore is global, distinct from the -m 'not slow' marker filter that only ./vol test adds. The docs/help imply test-all is exhaustive, so an agent trusts a 'complete' run that never touches those real-data tests.

**Recommended fix:** Prefer the finding's ALTERNATIVE fix (doc correction), NOT its primary fix. The primary fix (drop --ignore, gate tests/slow via marker so test-all + CI run it) would CONTRADICT the documented design in src/tests/slow/conftest.py: those tests "read real data from data/processed/ or data/raw/", which CI (ubuntu-latest, no data checkout) lacks — they'd fail. Instead: (a) clarify docs so the tests/slow/ DIRECTORY is described as a real-data staging area excluded from all automated runs and invoked explicitly via `pytest tests/slow/`, distinct from the @pytest.mark.slow marker that test-all does include; and (b) optionally rename the directory (e.g. tests/realdata/) to remove the collision with the `slow` marker.

### AW-39 — CI lacks cost controls (no paths filter, no concurrency cancel, no dep cache) and runs bare uv/mypy/pytest with flags that diverge from ./vol typecheck

**LOW · optimization · effort: trivial · ADJUSTED-CONFIRMED**

**Location:** `.github/workflows/ci.yml:3` · `.github/workflows/ci.yml:28` · `vol:244` · `.github/copilot-instructions.md:67`

**Evidence:** CONFIRMED cost-control gaps only: ci.yml:3-7 no `paths:`/`concurrency:`; line 28 `uv sync --dev` with no cache (setup-uv@v3 line 25 lacks `enable-cache`); job scoped to src/ (line 14) yet 588/895 tracked files (65.7%) live outside src/, so docs/memory/skills-only PRs run the full lint+test suite. REFUTED sub-claims: (1) mypy flag difference (ci.yml:37 `--ignore-missing-imports` vs vol:244 none) is NOT a defect — vol:54-74 relies on GS system-site-packages (pytickclient/pyslang/gs_quant) absent in CI, so `--ignore-missing-imports` is required; and the divergence direction is opposite the "why" (vol is stricter → fails locally, passes CI). (2) CI does not run `uv run python` (copilot-instructions.md:67); it runs `uv run ruff/mypy/pytest` — the relevant rule is #2, and CI is a distinct env where vol cannot run, so the "hypocritical" framing is optics not a functional defect.

**Why it matters:** Every docs/memory/skills-only PR burns a full runner running tests it can't affect; local ./vol typecheck is stricter than CI so an agent can pass locally and fail CI; the bare-command CI reads as hypocritical next to the 'zero exceptions' rule.

**Recommended fix:** Add `paths: ['src/**', '.github/workflows/ci.yml']` and a top-level `concurrency: {group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true}`; set `enable-cache: true` on astral-sh/setup-uv@v3 (line 25). Do NOT align mypy flags or route CI through ./vol — vol is hardwired to the GS nix/Coder env (LD_LIBRARY_PATH from /nix/store, sed on pyvenv.cfg, system-site-packages for GS-internal pkgs) and cannot run on ubuntu-latest; CI's `--ignore-missing-imports` is necessary precisely because those packages are absent in CI. Optionally add a comment noting CI is the sanctioned bare-command context (distinct from the vol-wrapped GS dev env).

### AW-49 — Boot-protocol session-handoff check reads a file nothing writes, and the memory system is unreachable from plain Copilot chat

**LOW · broken · effort: small · CONFIRMED**

**Location:** `AGENTS.md:58` · `workflows/bootup.md:21` · `.github/copilot-instructions.md:48`

**Evidence:** Repo-wide grep for session-handoff.md: 2 hits, both readers (AGENTS.md:58, bootup.md:21); no workflow/skill/prompt writes it. Boot reads live only in AGENTS.md:54-57; copilot-instructions.md's sole memory mention is 'memory … exempt' with no load instruction.

**Why it matters:** Boot step 4 is a permanent no-op (no producer) and its md-link makes lint_broken_refs FAIL every run. On surfaces that inject only copilot-instructions.md, the P0 files/INDEX/rules silently never load — behavior diverges by surface with no error.

**Recommended fix:** Add a 'write session-handoff.md at session end' step (or delete boot step 4) and convert the link to backtick text; add a 3-line boot pointer to copilot-instructions.md so both injection paths converge.

### AW-50 — Dead routing pointers in live surfaces: phantom skills (APPDIR_API, CPNL_SUPPORT, GET_ISSUANCE_TASKS), renamed package src/ml_vol_estimator/, and moved docs

**LOW · broken · effort: trivial · CONFIRMED**

**Location:** `skills/DIRGET/SKILL.md:32` · `skills/PROCMON_JOBS/SKILL.md:14` · `skills/PROCMON_LOGS/SKILL.md:67` · `.github/prompts/status.prompt.md:29` · `.github/prompts/feature.prompt.md:26` · `.github/prompts/gsvivs-audit.prompt.md:155`

**Evidence:** DIRGET:32 'use APPDIR_API' (renamed CANVAS); PROCMON_JOBS:14 'Called by CPNL_SUPPORT' (nonexistent); PROCMON_LOGS:67 GET_ISSUANCE_TASKS (nonexistent); status:29 + feature:26 'src/ml_vol_estimator/' (dir is src/volforecast/, used correctly 15 lines earlier); gsvivs-audit:155 workspace/docs/gsvivs_iv_improvement_plan.md (missing).

**Why it matters:** Each is a routing instruction to a nonexistent target: agents search for a missing skill and fail, /status lists modules from a directory that doesn't exist (internally inconsistent output), and the dispatch guidance dead-ends.

**Recommended fix:** s/APPDIR_API/CANVAS/; delete/rewrite the CPNL_SUPPORT and GET_ISSUANCE_TASKS sentences; s|src/ml_vol_estimator/|src/volforecast/| in status:29 and feature:26; repoint gsvivs-audit:155 to workspace/research/.

### AW-51 — gsvivs-audit.prompt.md is a completed one-shot dated analysis stored as a permanent slash command with a missing primary input

**LOW · organization · effort: small · ADJUSTED-CONFIRMED**

**Location:** `.github/prompts/gsvivs-audit.prompt.md:18` · `.github/prompts/gsvivs-audit.prompt.md:141` · `.github/prompts/gsvivs-audit.prompt.md:148`

**Evidence:** :20 'From a preliminary analysis of the first 5 days (2022-05-25 to 2022-06-01)' (header at :18); :140 'The file is `data/external/output.json`' (also :10) — git ls-files shows no data/ or output.json tracked; :148 'Read `.github/copilot-instructions.md` before starting' (redundant, always injected). 6824B confirmed largest prompt (next: slang-review 6227B), ~1706 tokens, spent only on slash-command invocation, not per-request. No file references gsvivs-audit, so relocation is safe.

**Why it matters:** Prompt files should be reusable capabilities; this dated analysis fails at step 1 on missing runtime data, pollutes the picker with ~1.7k tokens, and its stale 'What We Already Know' misleads future runs.

**Recommended fix:** Move the body to workspace/research/ as a task record; if a reusable audit is wanted, keep a ~15-line parameterized prompt (argument-hint for JSON path), dropping the 5-day narrative and the redundant :148 line.

### AW-52 — Unreviewed machine-edit debris in SKILL.mds: corrupted headings and duplicate step numbering across 3 skills, triple-pasted section in another

**LOW · quality · effort: trivial · CONFIRMED**

**Location:** `skills/ETASK/SKILL.md:54` · `skills/ETASK/SKILL.md:67` · `skills/SECDB_TRANSLOG/SKILL.md:152` · `skills/PYTHON_MARKET_DATA/SKILL.md:110` · `skills/KILL_ORPHANS/SKILL.md:78`

**Evidence:** ETASK '## CList Open Tasks' / '### LI Commands' (edit debris from 'List'/'CLI'); SECDB_TRANSLOG two step-3s (152-155); PYTHON_MARKET_DATA two '### 3.' (110, 118) so steps off by one; KILL_ORPHANS identical Troubleshooting table 3x (78-96).

**Why it matters:** Mangled headings orphan command trees under meaningless anchors and break section-anchor navigation the SEARCH skill relies on; duplicate ordinals invite skipped steps; all signal unreviewed generation, lowering trust in the files.

**Recommended fix:** Fix headings ('## List Open Tasks (Aggregated)', '## CLI Commands'); renumber the duplicated steps; delete two of the three KILL_ORPHANS Troubleshooting copies.

### AW-53 — Model-pinning and routing rules restated in prose across many files (8+ workflow copies, 4 routing copies) with a dead 212-byte routing.md stub

**LOW · context · effort: trivial · ADJUSTED-CONFIRMED**

**Location:** `AGENTS.md:7` · `workflows/INDEX.md:13` · `workflows/_protocol.md:13` · `policy/routing.md:5` · `workflows/execute.md:35` · `workflows/execute.md:106`

**Evidence:** Routing rule (same skeleton, minor wording drift) appears in AGENTS.md:7, workflows/INDEX.md:13, workflows/_protocol.md:13, and policy/routing.md:5 (212B stub, wc -c). Subagent model-pin prose "Claude Opus 4.6" restated in workflows/execute.md:35 and :106, research.md:88, refactor.md:88, and canonical policy/subagent_protocol.md:14 (plus AGENTS.md:23). Note: workflows/plan.md has no prose pin — only .github/prompts/*.prompt.md carry functional `model: Claude Opus 4.6` frontmatter. policy/index.md:24's catalog entry describes routing.md as a "(prompt→keyword→pattern→effort)" pipeline that the 6-line stub does not contain — a stale inbound ref.

**Why it matters:** N copies of one-sentence rules mean any change needs a multi-file sweep; routing.md adds an indirection hop with zero unique content and its inbound refs are already stale.

**Recommended fix:** Delete policy/routing.md and remove/repoint its policy/index.md:24 catalog line (else it dangles). Keep AGENTS.md:7 as canonical routing; change workflows/INDEX.md:13 and _protocol.md:13 to "Routing: see AGENTS.md". Replace prose model pins in execute.md (2), research.md, refactor.md with "per subagent protocol (policy/subagent_protocol.md)", keeping subagent_protocol.md canonical. Leave .github/prompts/*.prompt.md `model:` frontmatter alone — it is functional per-prompt config, not restated prose.

### AW-54 — PYTHON_PATH ships a 4.8KB Python resolver nothing references, and _run.cmd bypasses the skill's central-resolution mandate

**LOW · architecture · effort: small · ADJUSTED-CONFIRMED**

**Location:** `skills/PYTHON_PATH/src/resolve.py:6` · `skills/PYTHON_PATH/SKILL.md:83` · `skills/_shared/_run.cmd:16`

**Evidence:** grep 'resolve.py' across tracked tree: only its own docstring (skills/PYTHON_PATH/src/resolve.py:6). resolve.py is 4851 bytes (wc -c). resolve.ps1 is named in only 2 tracked files (SKILL.md, memory/ref/skill-scripts.md:28) — NOT "10+ consumers." Consumer SKILL.md files reference "the PYTHON_PATH skill" narratively (e.g. CANVAS/SKILL.md:105, SECDB_DIFF/SKILL.md:32). The actual runtime path is 30+ *_task.cmd wrappers calling skills/_shared/_run.cmd, which runs its OWN hardcoded scan `for %%V in (315 314 313 312 311 310 39 38)` (_run.cmd:31-32) — never touching resolve.ps1 OR resolve.py. Meanwhile SKILL.md:83 mandates "Never hardcode a Python path in commands. Always resolve first," and resolve.ps1's documented order prefers user.json/venv311 (SKILL.md:37-40) while _run.cmd prefers highest venv — so the two can diverge. A third path exists: MODEL_TRAIN/src/train_task.cmd:43 and NOTEBOOK/src/notebook_task.cmd:41 call bare `python` after `H:\all-languages-env.cmd`, bypassing both.

**Why it matters:** Two independent resolution algorithms (resolve.ps1 reads user.json; _run.cmd scans a hardcoded venv range) can pick different interpreters for the same skill by entry path; resolve.py is dead weight in the most-depended-on utility skill.

**Recommended fix:** Delete resolve.py (nothing references it) or, since its docstring says "cross-platform" and it handles Linux+Windows, document it in SKILL.md as the POSIX/cross-platform variant of resolve.ps1. Separately, make _run.cmd read workspace/config/user.json's python_path first (matching resolve.ps1's order) before its H:\venv315..38 scan, so the runtime task path and the documented resolver agree. Note MODEL_TRAIN/NOTEBOOK *_task.cmd also bypass resolution with bare `python`.

### AW-55 — memory/ref/vol-cli.md 'mirror' documents only 19 of 33 vol commands (omits the mandated test-all gate), pushing agents to run ./vol help

**LOW · context · effort: small · ADJUSTED-CONFIRMED**

**Location:** `memory/ref/vol-cli.md:13` · `vol:98` · `vol:220` · `.github/copilot-instructions.md:26`

**Evidence:** vol-cli.md:13 "mirrors ./vol help" but documents 19 unique commands (22 table rows incl. 4 run-variants) vs 33 dispatch cases in vol; omits test-all (vol:98 "Run `test-all` before committing.", dispatch vol:220) plus notebook, ingest-ohlcv/-ticks/-iv/-xasset/-corr/-micro/-edrvs, kvar, cache-status/-clear, present. test-all never appears in AGENTS.md/copilot-instructions.md/vol-cli.md. copilot:26 advertises "./vol help | Full command reference". The fallback ./vol help output (vol:83-210) is 8,256 bytes ≈ 2,060 tokens, not ~1,150.

**Why it matters:** The cheap on-demand doc is unreliable, so agents fall back to executing ./vol help (~1,150t into the terminal buffer) and never learn test-all before commit (skipping slow LSTM/subprocess tests); staleness converts a static doc into repeated runtime cost.

**Recommended fix:** Regenerate vol-cli.md from `./vol help` (add the 14 missing rows) with a lint step diffing the two, mirroring the yaml-config canonical-example rule.

*Phase 2 · Quick wins*

## ROI-ranked, ≤15 min each

High-impact and low-effort. Do these first, in order.

1. **Revoke both Confluence PATs; untrack and gitignore `workspace/config/.env`.** Stops active credential exposure. `git rm --cached`, add `/workspace/config/.env` + `*.env` to `.gitignore`, ship `.env.template`, then purge history. The CONFLUENCE skill already reads the PAT from this local env file, so untracking breaks nothing. AW-01 · AW-10 · AW-33
2. **Add `/workspace/tmp/` to `.gitignore`.** Prevents the ~24h GSSSO SSO cookie (written cleartext to `workspace/tmp/gssso_cookie.txt`) and stale task args-files from ever being committed. One line. AW-33 · AW-04
3. **Delete `commandAllowlist terminal:["*"]` and `additionalReadAccessPaths:["h:/"]` from the workspace file.** Removes the auto-approve-everything gate and whole-drive read grant. If auto-approval is wanted, use the real `chat.tools.terminal.autoApprove` with an explicit command map. AW-03
4. **Fix the renamed-package dead paths: `s|src/ml_vol_estimator/|src/volforecast/|` in `feature.prompt.md:26` and `status.prompt.md:29`.** `/status` currently lists modules from a directory that doesn't exist; `/feature` routes to a phantom path. Same edit fixes both. AW-25 · AW-50
5. **Rename `'fix it.prompt.md'` → `fix-it.prompt.md` and reconcile the `/fix it` trigger.** The space collides with Copilot's built-in `/fix`, likely stranding the 16 KB `fix.md` pipeline. Add `name: fix-it` or `git mv`. AW-37
6. **Fix the mandated CV import: `from volforecast.utils.cv import PurgedKFoldCV`.** `python.instructions.md:46` teaches `volforecast.utils.time_series.PurgedKFold` — a module that raises `ModuleNotFoundError`. Delete the stale embedded class too. AW-14
7. **Correct the `EDRVOL_PERCENT` → `ERDVOL_PERCENT_STANDARD` dataset-id typo in `python.instructions.md`.** A transposed-letter, dropped-suffix wrong-dataset landmine in an always-attached instruction file. AW-19
8. **Fix both `git add -A` examples in `GIT/SKILL.md` to explicit staging.** The flagship “Full push workflow” example violates the same file's own rule 25 lines below it. AW-45
9. **Change the `ale_features` documented default `top_10` → `top_20` in `yaml-config.instructions.md:176`.** The doc contradicts both the code (`config.py:237`) and its own example two tables up. AW-G26
10. **Re-fence the 5 `````powershell`` blocks that use `cmd`-only `^` line continuation.** Copied into PowerShell as labelled, every one runs the tool with a literal `^` arg. Fence as `````cmd`` or use backtick continuation. AW-46

*Phase 2 · Strategic recommendations*

## The bigger restructurings

Seven moves that address root causes rather than symptoms. Each maps to the findings that motivate it.

### S1 — Treat the credential leak as a security incident, not a cleanup.

Revoke/rotate both PATs, report per firm policy, purge internal-only material (endpoints, employee PII, auth-flow docs) from the off-perimeter copy, and flip all 8 TLS-verification-off clients to `create_default_context()` with the GS CA bundle. The repo's own guidance (`confluence-auth.md:78`) already forbids what was done.

**Motivating findings:** AW-01 · AW-02 · AW-08 · AW-10 · AW-32 · AW-33

### S2 — Declare supported execution environments and stop mandating one universal path.

Scope the `./vol` mandate to `src/` Python on the Linux/Coder workspace; acknowledge the skill layer's per-OS `.sh`/`.cmd` wrappers; carve a `run_in_terminal` exception for environments without `run_task`. Then *decide whether the Copilot coding agent is a supported consumer* — if yes, add `.github/workflows/copilot-setup-steps.yml` + a folder-scoped `.vscode/tasks.json`; if no, one always-on line scoping it out. Today both branches are dead.

**Motivating findings:** AW-07 · AW-05 · AW-13 · AW-G9 · AW-G10 · AW-G11 · AW-G12 · AW-G14

### S3 — One source of truth per rule; everything else points.

`copilot-instructions.md` owns the 9 `HARD` rules; `AGENTS.md` replaces its restatements with the existing one-line pointer. The ML Key-Constraints table lives once (AGENTS.md); personas/instructions say “apply Key Constraints.” The context-packet schema lives only in `subagent_protocol.md`. Resolve the drifted values (`ruff` in the never-run list, `/team` depth 1-vs-2, lint on/off).

**Motivating findings:** AW-14 · AW-22 · AW-26 · AW-27 · AW-28 · AW-35 · AW-53

### S4 — Make the lint suite a real gate, and lint what it can't yet see.

Wire `lint_all.py` (stdlib-only, 2.4s) into CI and pre-commit; fix the current 3/14 failures so the gate is green and meaningful. Then close the blind spots the rot exploited: plain-text repo-relative refs, `_dormant` as a source tree, prompt `model:` values against one shared constant, and each task's `--args-file` against the filenames its SKILL.md promises.

**Motivating findings:** AW-21 · AW-12 · AW-04 · AW-23 · AW-34 · AW-47

### S5 — Prompts are dispatchers, never procedure copies.

Rewrite `backtest`/`feature`/`research` prompts as thin dispatchers (mode + persona + link to the owning skill/workflow) and defer all parameters to the skill — today they fork the skill with drifted cost models and skip the workflow's FOCUS gate. Add the rule to `skills/design.md`, add a `.github/prompts/INDEX.md`, and prefix every verbless prompt body with “read these files first” (Copilot attaches nothing for backtick paths).

**Motivating findings:** AW-11 · AW-25 · AW-43

### S6 — Make the memory budget real and the two-tier design honest.

Compute `INDEX.md` tokens from bytes, add existence + Status/Updated columns, demote the fat P1s under the 50k cap, and delete dead rows. Repoint the forked research journal (INDEX routes to a copy 8 weeks stale). Give `_dormant` an actual state in the lifecycle and a restore procedure — 10 skills depend on it in-place.

**Motivating findings:** AW-15 · AW-16 · AW-17 · AW-34 · AW-48

### S7 — Move the personal-tutoring machinery out of the work repo.

Six of 34 slash commands and ~490 KB of mastery-state + a generated `dashboard.html` are personal-learning tooling in a team-visible tree; `/study` alone loads a 194 KB graph (~48k tokens) per session. Collapse to `/study` + one `/learning`, add a due+frontier node selector, and relocate to VS Code user-profile prompts (or gitignore the dashboard).

**Motivating findings:** AW-24 · AW-40 · AW-18

### Target architecture — proposed ownership

```
# Single source of truth per concern. ← annotations mark the fix.
.github/
  copilot-instructions.md      ← OWNS the 9 HARD rules (+ boot pointer for chat-only surfaces)
  prompts/
    INDEX.md                   + NEW: registry so the 34 commands are discoverable
    *.prompt.md                thin dispatchers only: mode + persona + link (no forked runbooks)
    fix-it.prompt.md           renamed from 'fix it.prompt.md' (space collided with /fix)
  instructions/
    python.instructions.md     applyTo: src/**/*.py  (was **/*.{py,ipynb}); refs, no inlined code
    yaml-config.instructions.md enum tables regenerated from registries by CI
  workflows/
    ci.yml                     trigger includes default branch; installs deps for public runner
    copilot-setup-steps.yml    + NEW (or scope the coding agent out in one always-on line)
AGENTS.md                      OWNS project identity + Key Constraints; POINTS for HARD rules
.vscode/tasks.json             + NEW: 43 tasks mirrored out of the .code-workspace
.env  (gitignored)             was tracked with a live PAT — untrack + rotate
policy/                        wire 6 orphaned files to a loader, or fold unique detail up + delete
  subagent_protocol.md         SOLE home of the context-packet schema + depth table
skills/
  design.md                    + "prompts are dispatchers" rule; reconcile 48-vs-54 roster
  <SKILL>/SKILL.md            run_task (not create_and_run_task); _dormant refs → live paths
memory/
  INDEX.md                     token math from bytes; +Status/Updated cols; existence-checked
  research/research-journal.md → pointer card to the live workspace/ twin
  _dormant/                    real lifecycle state + restore procedure; linted as source
workspace/lint/lint_all.py     wired to CI + pre-commit; 3/14 failures fixed; new ref/model linters
vol                            OS guard: fail loudly off Linux/nix instead of silently
```

*Phase 0–2 · Coverage & method*

## What was inspected — and what wasn't

#### Read fully

Both always-on files, both instruction files, all 34 prompts, all 48 `SKILL.md` + `skills/_shared/`, all 18 lint modules, all 14 policy + 7 persona + 18 workflow files, the `vol` wrapper, active memory (10 largest fully, rest skimmed), `_dormant` (8 largest fully), and the `.code-workspace` task defs. The 14-check lint suite was executed (`3/14 FAIL`).

#### Verified independently by the orchestrator

The committed `.env` PAT and its gitignore status (reproduced), the always-on token chain (~10,235 t), all directory/file existence references in `AGENTS.md`, and clean per-class byte sums from `git ls-files`.

#### Deliberately skipped

The excluded snapshot trees `ml-vol-estimator/`, `qr-decode/`, `.claude/` (never cited). `src/**` product code was grep-swept for secrets/TLS issues (clean) but not reviewed for logic. `workspace/scripts/` (15 one-off analysis scripts, zero agentic refs) inventoried, not audited.

#### Open hypotheses (stated, not asserted)

Whether `Claude Opus 4.6` is currently a selectable Copilot model and what VS Code does with an unavailable pin (AW-G2/G3/G4); whether the GS-fork VS Code honors the non-standard `commandAllowlist`/`additionalReadAccessPaths` keys (AW-03); exact resolution of a space-containing prompt basename (AW-37). Each finding marked `hypothesis` names what would confirm it.

#### Verification economics

176 inventory candidates + 95 dimension findings → merged to 55 (0 dropped) → adversarial verify kept 55 (0 refuted) → completeness critic surfaced 6 gaps → 31 gap findings → 29 verified. Final 84. Severity reflects post-verification corrections, not the auditors' first pass.

#### Numbers discipline

Every “bloated / duplicated / expensive” claim carries a measured byte/token/occurrence count. Approx tokens = bytes / 4. Where an auditor's original number was wrong, the verifier's corrected figure is what appears above.

---

*Generated by a 141-agent audit workflow over the `ML-GS` git-tracked tree · findings are analysis-only, no files were modified · IDs `AW-01`–`AW-55` (dimension auditors) and `AW-G2`–`AW-G31` (gap-chase) · sorted `BLOCKER → LOW`.*
