# Daily Progress Log

---

## 2026-04-29

**Sprint:** 0 -- Onboarding & Scoping
**Focus:** Project kickoff

- Initial commit: ML Signal Discovery internship project repository created
- Set up repo structure with deliverables/, reference/, notes/ directories
- Began drafting initial pitch for supervisor meeting

**Next:** Prepare pitch presentation for first team meeting

---

## 2026-04-30

**Sprint:** 0 -- Onboarding & Scoping
**Focus:** Pitch preparation

- Wrote v2 pitch presentation: 5-slide product pitch with 3 backup slides
- Added index product framing, two-tier structure, and replicability Q&A sections
- Speaker script drafted and polished for delivery
- Redesigned presentation to remove IC speculation and jargon -- kept it clean and product-focused

**Next:** Deliver pitch, begin learning guide, start scoping data access

---

## 2026-05-01

**Sprint:** 0 -- Onboarding & Scoping
**Focus:** Volatility learning guide creation

- Designed and wrote vol learning guide spec and implementation plan
- Built full LaTeX infrastructure (memoir class, preamble, tcolorbox environments)
- Wave 1 chapters: Ch 1 (stylized facts), Ch 5 (GARCH), Ch 8 (options/vol surface), Ch 16 (forecast evaluation)
- Wave 2-3 chapters: Ch 2 (RV theory), Ch 3 (microstructure), Ch 4 (jump detection), Ch 6 (HAR), Ch 9 (VRP)
- Ch 7 (rough volatility) written -- 649 lines covering fBM, Hurst estimation, rough Heston
- ML chapters: Ch 10 (feature engineering), Ch 11 (tree methods), Ch 12 (deep learning), Ch 13 (ensembles), Ch 14 (multivariate), Ch 15 (spillovers)
- 16 chapters written in one session covering the full theoretical foundation

**Next:** Fill practitioner gaps in guide, curate project-specific papers

---

## 2026-05-05

**Sprint:** 0 -- Onboarding & Scoping
**Focus:** Guide refinement, paper curation, repo restructuring

- Curated 19 ML vol forecasting papers into reference/project-papers/
- Prepared supervisor update speech summarizing first week progress
- Added practitioner gap sections: Dupire local vol, variance swap mechanics (Ch 8), gamma P&L and delta-hedging economics (Ch 9), path-dependence bridge (Ch 7), adverse selection bridge (Ch 3), microprice and volume features (Ch 10), event-driven vol features (Ch 10), vol targeting and dealer gamma (Ch 17)
- Retrofitted all 17 chapters with plain English translations and project connection boxes
- Consolidated bibliography and fixed cite key mismatches across all chapters
- Resolved all LaTeX compilation errors -- guide compiles cleanly
- Reorganized repo: archived stale Risk-as-Alpha spec/plan files, added custom skills (.claude/skills/), set up /sync-docs skill for docs-only branch workflow
- Compiled all guide PDFs and synced to docs-only branch

**Next:** Document data access, decide on project direction, write design spec

---

## 2026-05-06

**Sprint:** 0 -- Onboarding & Scoping
**Focus:** Project direction decision, design spec, implementation plan

- Documented full data access inventory (notes/data-access.md): tick-level RV for 34 symbols, E-mini L2 microstructure, SPX IV surface from ERDVOL, cross-asset signals
- Evaluated 5 project directions against data access constraints -- selected Direction 1+5 hybrid: "Layered Information and Realized Volatility: Where ML Adds Value Beyond HAR"
- Wrote comprehensive design spec (8 sections): project identity, architecture, evaluation framework, signal specification, timeline, documentation system, risk register, out of scope
- Spec reviewed and 13 issues fixed (holdout test set, sign conventions, expanding-window CV, cost mechanics, regime thresholds)
- Wrote full implementation plan: 27 tasks across 4 chunks (Sprints 1-6), Sprint 1 with complete TDD code
- Plan reviewed by 4 parallel reviewers, all issues resolved (missing multi-horizon targets, HAR-J/HAR-CJ, DSR formula, straddle direction, BPV passthrough)
- Archived Risk-as-Alpha deliverables to archive/ directory
- Decision: project direction locked in as Layered Feature Value (HARQ-X + ML with IV-RV gap signal)

- Executed Task 0: created volforecast/ package skeleton with data/, features/, models/, evaluation/, signals/, utils/ modules
- Default config with universe, horizons, CV params; progress-log skill with post-commit hook; editable pip install verified

**Next:** Begin Sprint 1 -- Task 1 (units.py), Task 2 (rv.py), Task 3 (universe.py)

---

## 2026-05-12

**Focus:** Deep technical review of GS codebase documentation

- Received comprehensive codebase doc from GS machine (notes/ml_vol_forecasting_docs.md, 1988 lines): documents entire volforecast package (v0.2.0, 50 files, ~150 functions, 390 tests)
- Designed and executed 6-pillar audit via 3 parallel research agents: math correctness, architecture + ML practices, ensemble/stacking research
- Math verification: checked 16 formulas against papers. Found 6 issues (2 Important: semivariance indicator > vs >=, BNS uses RQ instead of RTQ; 1 Important: QLIKE log-space sign convention may be reversed)
- Architecture review: discovered 2 Critical issues (FeatureLayer protocol cannot serve Layers 2-5, CV purge gap not enforced for h >= 22)
- Ensemble research: revised strategy from "stacking at h=1/h=5, blending at h=22" to prediction blending at all horizons, based on cross-referencing Christensen et al. 2023, Bucci 2020, Fed 2025, Optiver evidence
- Debt triage: re-prioritized 13 items, added 3 new (FeatureLayer context, purge enforcement, SQLite tracking). 5 P0 items total
- Produced Top 5 Actions roadmap for next 16 weeks, phased timeline, minimum viable deliverable definition
- Wrote 3 session prompts for upcoming work (review, project ref update, Copilot prompts)
- Updated memory with two-repo setup (planning repo here, implementation on GS machine)

**Next:** Session 2 -- update vol-project-ref guide with project plan chapter and development roadmap

---

## 2026-05-31

**Focus:** Agentic workflows -- highest-value workflow analysis + a reusable deep-research engine

- Ran a multi-agent workflow (32 agents) to map the repo and rank candidate workflows by value; top pick was a feature-evidence dossier, then pivoted to a more general capability
- Built `.claude/workflows/deep-research-distill.js`: reusable, parameterized engine (Scope -> parallel Harvest of arXiv/SSRN/GitHub/web -> adversarial Verify -> Distill into the repo). Invoke by name with `args={question, slug, depth}`
- First run -- "What beats HAR for daily RV forecasting in 2024-26?": 87 sources harvested, 11 adversarially verified and kept; brief written to `notes/deep-research/2026-05-31-what-beats-har-2024-26.md`
- Verify phase caught two fabricated figures and a wrong window spec already sitting in our notes; corrected har-components.md and the QLIKE-vs-MSPE record
- Hardened the workflow to parse JSON-string args (slug/depth were being dropped)

**Next:** Decide univariate-RV vs realized-covariance focus; port JLDC/HARd-to-Beat as the HAR baseline harness on the GS machine

---

## 2026-07-05

**Focus:** Repo tooling -- no-.py guard for the docs-only branch

- Added a git pre-commit hook enforcing that docs-only never contains `.py` files (restricted machines flag them): auto-renames staged `.py` to `.py.txt`, plus an index-level fail-safe that aborts the commit. Source of truth `.githooks/pre-commit` on main, installed at `.git/hooks/pre-commit` (can't use core.hooksPath -- tracked files vanish from the working tree on docs-only)
- Renamed the one existing offender on docs-only: deliverables/desk-pitch-2026-07/generate.py -> generate.py.txt
- Gitignored ml-vol-estimator/ on both branches -- the sync-docs `git add -A` step would otherwise sweep the 909-file local GS repo copy into docs-only on the next sync
- Updated /sync-docs Step 4 (explicit .py rename + `git add` scoped to guides/deliverables/notes) and the CLAUDE.md docs-only section
- Overhauled the Claude Code hook system (3 commits, planned via docs/superpowers/plans/2026-07-05-hook-improvements.md). Discovered the three PostToolUse bash one-liners had never fired: they grepped a `$TOOL_INPUT` env var Claude Code doesn't set (hook input is stdin JSON), and plain PostToolUse stdout is invisible to the model anyway. Replaced with `.claude/hooks/posttool-nudge.js` emitting `hookSpecificOutput.additionalContext` (chapter-mirror nudges for both guides incl. the ch12/ch12b slug collision, plus the git-commit progress-log nudge) -- verified live in-session
- Extended the guide-autosync Stop hook to cover vol-project-ref alongside vol-learning-guide: JSON marker map (legacy bare-hex migrates), silent seeding of newly covered guides so fresh clones don't trigger a spurious full regen+push, root via CLAUDE_PROJECT_DIR instead of a hardcoded path, 17 node:test unit+integration tests
- Moved hook wiring into tracked `.claude/settings.json`; `settings.local.json` now holds only the machine-local permission mode; added `.claude/hooks/README.md`
- Noted: uncommitted prose-editing changes across all three guides' chapters are sitting in the working tree (not mine, left uncommitted); once committed, the Stop hook will correctly demand a mirror regen + sync-docs for both covered guides

---

## 2026-07-06

**Focus:** De-slopping all three LaTeX guides (unslop + unslop-text) end to end

- Ran a two-pass de-slop workflow over 77 chapters + 3 main.tex (~365k words, 160 agents): pass 1 applied the unslop methodology per file (em dashes, antithesis cadences, throat-clearing, filler diction; math/citations/tables/TikZ/box structure sacred); pass 2 ran the unslop-text audit and adversarially verified every diff hunk
- Results: prose em dashes 1,620 -> 85 (all survivors are table empty-cell placeholders or sacred box titles), scanner slop score 484 -> 384 with the residual being protected domain terms (leverage effect, robust estimator, elevated vol). Structure delta-gate (brace/env/$ parity + cite/ref/label counts vs baseline snapshot) OK on all 80 files
- Pass 2 earned its cost: caught and repaired real pass-1 damage -- comma splices, double colons from dash->colon swaps, one dropped clause, several weakened technical claims ("critical", "elevated", "robust" chased too hard)
- Mid-run session-limit outage killed 40 of 80 verify agents; resumed the workflow from its journal cache so only the missing 40 re-ran
- Compile gate: all three guides build clean (vol-learning-guide 369pp, quant-trading 570pp, vol-project-ref 55pp, zero LaTeX errors)
- Mirrored the 199 rendered tex hunks into the markdown copies (22 agents, 20 files changed, 0 reconversions, 0 em dashes in mirrors)
- 3 commits to main (tex, markdown, PDFs) + push; docs-only synced + pushed (restores vol-learning main.pdf and markdown/ that an earlier branch cleanup had dropped)

- Follow-up: user caught that the vol-learning-guide PDF was committed one pdflatex pass short of pagination convergence (TOC off by one page from mid-ch1). Verified via pdftotext diff (all 650 changed lines were page numbers/running heads; quant-trading and vol-project-ref text-identical on recompile), recompiled to the .toc/.aux fixpoint, recommitted, resynced docs-only
- Updated /sync-docs Step 2 and the CLAUDE.md docs-only recipe: compile to the .toc/.aux/.ind fixpoint (loop, max 5 passes, non-convergence warning) instead of a fixed 3-pass pipeline; verified the new snippet live on vol-project-ref (converged in 3 post-bibtex passes)

- Later session: ran `deep-research-distill` on regime detection + regime×GNN fusion for SPX RV (the Part II/III half of the GNN-and-regimes prompt; Part I was swept earlier today into `notes/deep-research/2026-07-06-gnn-cross-asset-vol.md`). 25 agents, 58 sources harvested, 15 kept, 13 adversarially verified; brief at `notes/deep-research/spx-rv-gnn-regime-pipeline.md`
- Acquired 11 new PDFs (9 to b-ml-rv-core/, 2 to d-graph-gnn/), including open-access recoveries of two paywalled journals (Ding et al. 2025 via Stirling STORRE, Nystrup et al. 2020 via DTU Orbit); README index updated; Wang et al. 2019 (Wiley) and Cartea et al. 2026 (SSRN) remain paywalled
- Verify pass caught fabricated table numbers in the Cho & Lee 2025 harvest extraction and corrected them against the live page; 2 verify agents died on API errors (Ardia 2018, Wang 2019) and their rows are marked "not verified this run" in the brief's evidence table
- Headline: filtered MS-probability-as-HAR-feature is the best-documented regime pattern (~5.1% QLIKE on CSI 300); jump models supersede HMMs for the detector; the regime×GNN fusion layer has no credible published incumbent — build order: regime feature into HAR first, regime-gated ensembles second, regime-conditioned graphs last

- Later session: ran `verify-all-diagrams` on guides/quant-trading (66 agents, ~35 min): 31 TikZ figure rows audited against the compiled PDF, 15 already clean, 15 fixed (legend occlusions, label collisions, illegible `\tiny` subscripts, a style-clobbering `every axis title` bug, and one real math error — a cancelling `*100` in the ch28 convexity term that made the blue curve rise on yield rises), 0 outstanding
- Adjudicated the workflow's 3 needs-human flags by viewing the final crops: 2 were confirm-pass false alarms (deterministic checker counting tcolorbox/pgfplots bbox pairs on the page crop), 1 was a duplicate discovery row — the two-panel Heston smile figure was double-counted (unlabeled panel at ch30:301 + labeled panel), two fixers fixed the same legend-occlusion defect, first apply won, second's oldBlock went stale (`apply_failed`). Audit report annotated with resolutions: `notes/diagram-audit/2026-07-06-audit.md` + contact sheet
- Fixed the Workflow-by-name invocation failure: `.claude/workflows/verify-all-diagrams.js` had CRLF endings, which the Workflow permission dialog rejects as hidden control characters; converted to LF and added `.gitattributes` (`.claude/workflows/*.js text eol=lf`) so `core.autocrlf=true` can't reintroduce it
- All quant-trading fixes are uncommitted in the working tree (workflow never commits); guide recompiles clean

**Next:** The brief's resolving experiment — rolling HAR-WLS ± filtered MS-GJR-GARCH probability on SPX 5-min RV (h=1/5/22, QLIKE+DM+MCS) — or presentation diagrams (2026-07-03 spec); commit the quant-trading diagram fixes after review

---

## 2026-07-07

**Focus:** vol-learning-guide GNN chapter (fundamentals -> SOTA -> project blueprint), written end-to-end autonomously

- Planned and wrote the new chapter `16-graph-neural-networks.tex` (printed ch. 17, ~34pp, 1,100 lines): distill.pub-based fundamentals arc (market-as-graph, tasks, representation/permutation invariance, GCN/MPNN/GN-block/GAT, GIN expressiveness, over-smoothing, tiny-graph corollary) + frontier arc (GHAR/GNNHAR with the full Table-1 ratio grid, contested graph construction, point-in-time leakage rules, DCRNN-HAR/GSP-HAR/EMGNN/SpotV2Net/GTN-VF under a "does it survive QLIKE?" audit table, hybrid wirings incl. BGNN gradient-fitting, regime frontier, skeptic's checklist, 5-step build order with go/no-go gates)
- Pipeline: design doc + implementation plan committed first (50fadd6, 99a0034); 24-agent workflow extracted all 17 d-graph-gnn papers page-anchored and downloaded 7 foundational GNN papers (GCN, GAT, MPNN, GraphNets, GraphSAGE, GIN, over-smoothing) into reference/papers/; write-chapter passes ran: condenser (21 edits applied), naive reader (16 clarity gaps patched incl. WL/injective/multiset, magnetic-Laplacian permissions, Hurst/Jaccard glosses), adversarial verifier vs the source PDFs (all 60 GNNHAR table ratios PASS; 8 CRITICALs found and fixed -- mostly overstated universals like "every FC beats every GLASSO" and wrong leakage Sharpe sub-ranges)
- Fixed 3 bib entries that were wrong in references.bib (ChenRobert2022 had wrong authors/title/arXiv -- silently fixing ch12's citation; ZhangCucuringuDong2023 stub; ZhangPuCucuringuDong2024 wrong DOI); added 26 entries
- 12 TikZ figures drawn and gated: geometric self-inspection fixed 3 label collisions; blind reviewer passed 11/12 and its one FAIL (fig 17.3 adjacency matrices "inconsistent") was itself verified wrong -- both matrices are 3-edge relabelings, reviewer hallucinated a 4th edge
- Recompiled to TOC fixpoint (406pp, zero errors/undefined refs); commits 46ddea1 (chapter+cross-edits in ch12/14/15+bib), 4adf562 (reference PDFs+catalog), c5c07b4 (PDF); markdown mirror conversion delegated (in flight at entry time)
- Ops note: first verifier fan-out died on the Fable 5 usage cap mid-run; re-ran as a single sequential agent post-relogin

- Later session: wrote the complete GNN implementation plan set for ml-vol-estimator -- `deliverables/gnn-implementation-plans/` (00-overview + plans 01-10, ~4,400 lines): graph-construction library (8 point-in-time builders incl. GLASSO, directed DY generalized-FEVD with hand-computed gold values, factor-residual), standalone `requires_graph` pipeline path, GHAR + the four-graph gate ablation, GNNHAR + STID control, attention upgrades (edge features / TransformerConv / spillover export), DCRNN-HAR with a generic warmup contract, GSP-HAR (magnetic Laplacian) + MTGNN-style learned adjacency, 8-GPU orchestration (fold x GPU, seed x GPU, Optuna trial x GPU, per-GPU nested Rich bars), blend-vs-stack hybrids + PIT-frozen filtered regime probability + regime-blended graphs, and the grand tournament with turbulence-split QLIKE / conditional DM
- Every task in every plan carries the exact Copilot subagent context packet (repo `policy/subagent_protocol.md` schema: goal / file_scope / write_scope / acceptance_criteria / constraints / context_summary / depends_on) plus an orchestrator `/execute` prompt with wave ordering; everything TDD with failing-test code inline; experiments trial_079-090 fully specified with hypotheses, decision gates, and COVID statements
- Grounding: 8-agent exploration workflow (~1.8M tokens) over the GNN chapter, both deep-research briefs, the paper catalog, and five codebase maps (model layer, runner/experiments, progress/parallelism, data panel, dev workflow); key reconnaissance -- the repo already has a GATv2 (`models/gnn.py`) but only reachable via feature_stack->XGBoost, `n_gpus: 8` fold-parallel and multi-GPU Optuna patterns already exist for LSTM/XGBoost, and `torch-geometric>=2.4` is already a declared `graph` extra

- Sync session: committed the backlog to main -- plan set (81c1301), audit writeups incl. previously-staged-only copilot/LSTM/XGBoost deep dives (f328a4e), GNN briefs + diagram audit + journal + notes cleanup (4fdff34), quant-trading diagram fixes with recompiled 571pp PDF at pagination fixpoint after 3 passes (494af82) -- then synced docs-only (8116a42, +7,170/-2,530 across 24 files) and pushed both branches. Caught and reverted an over-eager deletion sweep before committing: files living only on docs-only (desk-pitch presentation, legacy faq/glossary/speaker script) stay; only the 6 note deletions committed on main propagated

- Evening session: copied the four audit deliverables (copilot-workflow-audit.html, src-codebase-audit, LSTM/XGBoost deep dives) from docs-only into main's `deliverables/` (secret-scanned, clean), then converted the 310KB copilot-workflow-audit.html into a faithful markdown mirror for agent consumption (bs4 class-aware converter: 84 finding cards with severity/dimension/effort/verdict chips, KPI + context-budget tables, 194-row inventory, S1-S7 recommendations; word-multiset fidelity check vs the HTML = zero missing words). The concurrent sync session committed a mid-conversion draft (f328a4e) while this ran; final corrected version committed as 2e8a1a6 (token-stack table, backtick-escaped `<placeholder>` tokens, AW-37 hypothesis tag) after splitting out 64 project-paper PDFs the commit had swept in from the index -- those are back to staged-uncommitted. Note: docs-only still carries the draft .md; next /sync-docs picks up the fix

- Built the reusable version of the plan-suite process as a skill + workflow (327e658): `.claude/skills/write-copilot-plans/` (SKILL.md + packet-schema/plan/overview templates) and `.claude/workflows/write-copilot-plans.js` (4 modes: recon fan-out with a mandatory verbatim contract map, judged design candidates through lenses, per-plan drafting against an authoritative interface ledger with packet lint, and cross-plan verify passes). Followed TDD-for-docs: baseline probe without the skill showed 5 gaps (no research grounding, solo design, no ledger, no plan verification, gate-free sequencing); with-skill probe closed all 5 and surfaced a real packet-schema discrepancy between the target repo's two policy files; one refactor from probe evidence (intermediate artifacts go to the session scratchpad, never the ml-vol-estimator mirror)

**Next:** copy the plan set to the GS machine as `workspace/plans/gnn/`, execute Plan 01 in a Copilot session, then run the trial_080 gate ablation

---

## 2026-07-08

**Focus:** authored the copilot-workflow-overhaul plan suite (remediate all 84 audit findings) via the new write-copilot-plans skill, end to end

- Ran the full skill pipeline against `deliverables/copilot-workflow-audit.md` (84 findings) targeting the `ml-vol-estimator` mirror. Output: `deliverables/copilot-workflow-overhaul-plans/` -- 00-overview + plans 01-08, ~8,500 lines, one Copilot `/execute` session per plan
- **Phase 0 recon** (10-agent fan-out, ~1.26M tokens): verbatim contract map (packet schema is the UNION of `subagent_protocol.md` + `context-isolation.md` + `plan.md`'s `depends_on`), governance/lint-suite map with measured-vs-claimed memory budgets, and a freshness probe confirming the mirror pre-dates all remediation -- 14/14 audit probes STILL-PRESENT (both live PATs, wildcard terminal allowlist, disabled lint gate, ~28 broken `_dormant` skill refs). Redacted the two PAT values the probe leaked into its report before persisting
- **Phase 1 design** (4 candidates x 3 adversarial judges): "execution-surface-realist" won (30.2/40) -- surfaces -> compute -> gates -> text sequencing; declares S-A (GS Windows, primary) + S-B (GS Linux Coder) SUPPORTED and the GitHub cloud agent UNSUPPORTED (can't reach *.gs.com); killer evidence was `utils/paths.py::resolve_project_root()` already listing `vol.cmd` as a root marker. Grafted red-then-green lint discipline, a scriptable 84-ID coverage matrix, and 5 separately-gated HUMAN-ACTION items (incl. the parent-repo `origin/presentation` branch that independently carries the token). User approved the decision record before drafting
- **Phase 2**: hand-wrote 00-overview with the plan table (gates A-E), a 25-row interface ledger, and the count-verified 84-ID coverage matrix (6 Blocker / 20 High / 40 Medium / 18 Low)
- **Phase 3 draft** (8 parallel drafters + packet lints): hit the Fable 5 session cap mid-run -- 5/8 returned structured output but all 8 files were fully written to disk (drafters that "failed" died on the return, not the write). Reconciled 17 reported ledger deviations; the load-bearing one was plan-06/07 assuming a `P0P1_BUDGET_ENFORCED` toggle + `lint_canonical_yaml.py` that plan-04 (the producer) never shipped -- back-ported plan-04's real names (grandfather-whitelist FILES burned to empty; `lint_canonical_schema.py`) into a ledger §6a addenda block
- **Phase 4 verify** (3-agent consistency/placeholder/rebuild): 19 findings (3 blocker, 8 major, 8 minor). Pinned canonical resolutions in a `fix-authority.md`, then fanned out one fix-agent per plan file. Blockers were all cross-plan seam drift (whitelist mechanism, the impossible "grep Opus 4.6 -> 0" end-state resolved with a `SANCTIONED_SITES` carve-out, a 14->15->21 lint-count off-by-one from plan-01's new check). Two real rebuild catches: plan-04 re-implementing an existing INDEX path-existence check, and plan-08's `select_nodes.py` re-deriving `generate_dashboard.py`'s due/frontier logic with guessed schema fields (`prerequisites`/`mastery`) that don't exist in the live data (`requires`/`tier`) and would have marked every node a frontier. Final grep sweep clean; suite converged
- First real-world exercise of the write-copilot-plans skill/workflow shipped in 327e658 the day before; it held up (recon caught the still-live incident, the ledger caught the parallel-draft drift, verify caught the rebuilds)

**Next:** on the GS box, copy the suite to `workspace/plans/copilot-workflow-overhaul/`, do the 5 HUMAN-ACTION items first (revoke both PATs), then run Plan 01 (`/execute`) through Gate A

---

## 2026-07-30

**Focus:** docs-only sync ahead of the GS hackathon; two repo-hygiene fixes surfaced by it

- Ran `/sync-docs`. All three guides reported no `.tex`/`.bib` changes, so nothing recompiled — the only content delta was `deliverables/hackathon-ideas.md` (top-5 shortlist for the 2026-07-30/31 GS hackathon: bug-report→failing-test agent, Ask-the-Data, compute-cost rightsizing, synthetic test data, desk-commentary drafting). Committed to main (f12d070), synced to docs-only (598a1bf), both pushed
- `.git/hooks/pre-commit` was **not installed** — the `.py`→`.py.txt` guard that CLAUDE.md relies on was absent, so the only thing keeping Python off docs-only was the `find ... mv` line in the sync recipe. Reinstalled from `.githooks/pre-commit`. Worth re-checking after any fresh clone; verified docs-only currently carries zero `.py` files
- Diagnosed why docs-only holds files main doesn't: the sync is **additive-only** — `git checkout main -- <paths>` adds and updates but never deletes, and `git add -A` sweeps in anything untracked sitting in the working tree at sync time. Two distinct causes: (a) files archived on main to `archive/risk-as-alpha/` (glossary, faq, secdb-data-requirements, speaker_script) linger on docs-only; (b) files that were **never on main** got swept in while untracked — `copilot-workflow-overhaul-plans/` (10 plans, ~8,400 lines) entered at sync f49db34 and exists nowhere else, likewise `2026-07-03-linear-alpha-tuning.md`, `notes/session-prompt-*.md`, `notes/vol-project-ref-audit.md`. `desk-pitch-2026-07/` is not drift — it came deliberately from the `presentation` branch (016cd62)
- Avoided repeating (b) this run by committing the hackathon file to main *before* the sync rather than letting `git add -A` catch it. User's call: leave the existing drift in place for now, so docs-only still carries the extra files
- Second `/sync-docs` run later in the day: no `.tex`/`.bib` changes, nothing recompiled; only delta was `deliverables/trailhead-walkthrough-spec.md`, synced to docs-only (c51b31e) and pushed

- Late session: merged the 10 remote hackathon/Trailhead commits into main (f285692) and pushed; only conflict was this file (both sides appended entries — kept both, 07-08 then 07-30). Incident during the merge: the first attempt failed against the leftover staged-uncommitted state (the 64 subfolder project-paper PDFs + 9 worktree edits from earlier `git pull --autostash` attempts), and a recovery `git reset --hard` wiped that index/worktree state. Fully recovered from the dangling autostash commit `4fc2846` (its tree = pre-session worktree, its `^2` parent = the staged 64): re-staged all 64 subfolder PDFs, restored the 9 modified files, verified all 32 backed-up b-/d- PDFs byte-identical. The uncommitted CLAUDE.md edits (78-paper subfolder line, per-snapshot `--sha` qr-decode paragraph) were re-applied to `CLAUDE.vol-project.md` since the remote commits swapped CLAUDE.md to the temporary hackathon version. Note: the flat→subfolder paper reorganization is still half-done — subfolder copies staged, flat originals not yet deleted, rewritten README uncommitted

**Next:** hackathon on 2026-07-30/31 (pick one of the top-5 and build it); afterwards, resume the plan set — copy to the GS machine as `workspace/plans/gnn/`, execute Plan 01, run the trial_080 gate ablation. Open hygiene item: decide whether to prune docs-only drift or back up the docs-only-only plan suite onto main

---

## 2026-07-31

**Focus:** hackathon day 2, Trailhead generator rebuilt to template parity (contract verified@3) and shipped to main

- Built the quality lock first (late 07-30 into today): hand-authored walkthrough of the restored ml-vol-estimator at `out/trailhead-mlvol-template.html` via a miniature pipeline (`template/`: 10 reader dossiers with verbatim quotes -> quote-to-line resolver -> sha256 -> splice -> independent verifier). 77 claims, 118 anchors re-hashed, zero em dashes; the build DELETED 20 authoring mistakes on first pass, which is the drop mechanic doing its job on me
- Root cause of the "it thinks it's a CLI tool" complaint: the QR restore is missing 14 modules the code imports (config.py x257 sites, pipeline/runner, models/har_family, models/lstm, evaluation/tournament, constants...). The ML core simply was not on disk for the narrator to see. The template and now the generator surface this as an on-page restore ledger instead of writing around it
- Generator upgrade, five workflows end to end: 8-reader dossier sweep of the 10k-line package -> frozen `docs/template-parity-spec.md` (@3 shapes) -> 6 parallel implementers on disjoint files (renderer swap, DAG-layered map columns + off-board tests, node:/dive:/gloss/tour/cols narrate packs with per-pack schemas, verify resolution+hashing of every new surface + dash policy, compose stats/restore-ledger/dive-stops/glossary, gates @3 + parity fixture + negative tests) -> integration (4 cross-boundary wires from the NEEDS lists) -> E2E on restored -> 3 adversarial judges -> ranked-fix round (regen provenance, glossary slug stripping, dive excerpt injection, honest where-table, rotating dive ledes, entry-first tour, reader-facing checkpoint provenance)
- The verifier caught the narration agents exactly as designed: 10 drops on the first full run (quotes from outside pack windows, one cross-file-ambiguous QLIKE docstring shared by lightgbm/xgboost, one 603-char role paragraph), all re-answered with in-window quotes rather than suppressed; final run 63 claims / 49 verified / 14 inferred / 0 dropped, 27 live glossary markers, both gates green, 587 pytest + 122 subtests green
- Overnight incident: 14 of 22 pack-answering agents died on the session cap (reset 2:10am) but several had already written valid answers before dying; a validation sweep separated real gaps (7) from partial writes, and one hash typo in my own workflow args was answered by hand
- Shipped as 4 commits to main (bc0a5c0, 99ee668, 3670b76, 4ee260c): generator, template+pipeline, regenerated artifact+narration store, skill docs

- Rewrote `hackathon/docs/confluence-trailhead.md` to the shipped state (b4963e3): leads with not-a-single-prompt mechanics, documents the @3 feature set with measured numbers, keeps a plain missing-features table (checkpoint breadth, glossary cap, trace discovery, unnamed AI tool, unmeasured time-saved)

- Pitch prep (efd1f97, pushed): replaced the `script.md` brain dump with a full spoken script (problem → product → checking mechanism → [DEMO HERE] → three takeaways → two-line close), layman wording throughout. A 3-lens review workflow (facts/layman/fluff) caught four would-be on-stage contradictions: "make your first change" exists in no shipped artifact (cut-list stop 12), Python-only scope was undisclosed, the "evidence or it's not on the page" close ignored visibly-marked `inferred` claims, and the staleness story overstated the shipped gate as self-detecting repo changes (reframed as re-running verification). Same commit: README de-duplicated via a find + devil's-advocate workflow — anchor/hash/delete mechanics now stated once in the verifier section, demo two-payload caveat merged to one paragraph, Known limits no longer restates the stage table; kept the flagged-but-load-bearing lines ("counted on screen", "credibility story", both headings)

- Fixed the reader-reported quiz giveaway (e272148, pushed): every order/rank checkpoint in the template artifact graded 1-2-3-4 top to bottom because `template/payload.mjs` authored options in the true sequence and `build.mjs` shipped them untouched — the Python generator shuffled, the miniature template pipeline never did. `build.mjs` now Fisher-Yates shuffles the (option, rank) pairs seeded from repo.commit + checkpoint id (identity draws re-roll), both verifiers (`template/verify.mjs`, `tools/verify-contract.js`) hard-fail an identity key, `checkpoints._order_block` redraws identity permutations with a seed-sweep test, and the four dossier/payload sentences that described the on-screen option order were reworded. Rebuilt artifact ships cp-c2 [1,4,2,5,3,6] / cp-d2 [3,2,1,4], keys hand-checked against the true sequences
- Same commit un-broke this Windows checkout's test run: `core.autocrlf=true` gives the worktree CRLF, which silently defeated `verify.mjs`'s payload-extraction regex (`};\n`) and all 13 `test_render.py` harness slices (`\n}\n`) — both now tolerate `\r\n`. Full suite back to green: 588 passed + 130 subtests, both gates and the template verifier pass

- Submission cleanup (ec40151): deleted the completed plans and dev-only artifacts — `briefs/`, six stale docs (implementation-plan, ideas-shortlist, data-lineage, demo-bundle-reference, both restyle/teaching prompt files), the abandoned `out/openclaw/` partial run, orphan `tests/narration/` outputs, and all local caches. Kept everything code references: template-parity-spec (cited from resolve/verify), `template/captures`+`dossiers` (read by build/payload.mjs), all of `out/` incl. the `.trailhead/` narration cache (byte-identical rehearsal replay). `restored/` untracked via `git rm --cached` + gitignore per user call — stays on disk, out of the submission. Gates + 588 tests green after
- Backed up all 12 generated bundles to `hackathon/backup/` (pipeline never writes there — live-demo fallback), then cut an orphan `hackathon` branch: single snapshot commit, `hackathon/` contents at branch root, 196 files, zero vol-project files or history (a subtree split would have carried restored/'s 1,063 borrowed files in past commits). README "Known limits" still claims 13 `test_render.py` failures — stale since e272148 fixed them; worth a one-line fix before submitting

**Next:** demo rehearsal against a genuinely unread repo (generate live on stage), decide the two open CLAUDE.md items (which internal GS tool Narrate names, demo repo choice); after the hackathon, restore CLAUDE.vol-project.md per the header note
